# PATH: GovScheme/tools/preflight.py
"""Offline project preflight checks for SmartGov AI.

This script deliberately avoids importing Flask so it can diagnose missing
runtime dependencies before the application is started.
"""
from __future__ import annotations

import ast
import glob
import os
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

errors = []
warnings = []

# 1. Python syntax
for filename in glob.glob("**/*.py", recursive=True):
    if any(part in {".venv", "venv", "__pycache__"} for part in Path(filename).parts):
        continue
    try:
        ast.parse(Path(filename).read_text(encoding="utf-8"), filename)
    except Exception as exc:
        errors.append(f"SYNTAX {filename}: {exc}")

# 2. Template references in Python
for filename in glob.glob("routes/*.py") + ["app.py"]:
    text = Path(filename).read_text(encoding="utf-8")
    for template in re.findall(r"render_template\(\s*['\"]([^'\"]+)", text):
        target = ROOT / "templates" / template
        if not target.exists():
            errors.append(f"MISSING TEMPLATE {filename}: templates/{template}")

# 3. Explicit template endpoint references.
# Flask endpoint names are collected from blueprint decorators.
routes = set()
for filename in glob.glob("routes/*.py"):
    tree = ast.parse(Path(filename).read_text(encoding="utf-8"), filename)
    bp_names = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "Blueprint" and node.targets
                and isinstance(node.targets[0], ast.Name) and node.value.args
                and isinstance(node.value.args[0], ast.Constant)):
            bp_names[node.targets[0].id] = node.value.args[0].value
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if (isinstance(decorator, ast.Call)
                        and isinstance(decorator.func, ast.Attribute)
                        and isinstance(decorator.func.value, ast.Name)
                        and decorator.func.value.id in bp_names):
                    routes.add(f"{bp_names[decorator.func.value.id]}.{node.name}")

for filename in glob.glob("templates/**/*.html", recursive=True):
    text = Path(filename).read_text(encoding="utf-8")
    for endpoint in re.findall(r"url_for\(\s*['\"]([^'\"]+)", text):
        if endpoint != "static" and endpoint not in routes:
            errors.append(f"UNKNOWN ENDPOINT {filename}: {endpoint}")

# 4. Database schema must be executable and contain required tables.
try:
    conn = sqlite3.connect(":memory:")
    conn.executescript((ROOT / "database/schema.sql").read_text(encoding="utf-8"))
    required = {
        "users", "schemes", "applications", "saved_schemes", "notifications",
        "eligibility_results", "recommendations", "scheme_updates", "automation_logs",
        "audit_logs", "rpa_jobs", "chat_sessions", "chat_messages", "complaints",
        "complaint_messages", "feedback", "admin_actions", "system_settings",
        "document_records", "application_events",
    }
    actual = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = required - actual
    if missing:
        errors.append("DATABASE missing tables: " + ", ".join(sorted(missing)))
    conn.close()
except Exception as exc:
    errors.append(f"DATABASE schema: {exc}")

# 5. Required project assets.
for required_path in [
    "requirements.txt", ".env.example", "database/schema.sql",
    "data/Government_Scheme_Eligibility_Upgraded.xlsx",
    "ai/train_model.py", "ml_models/trained_model.joblib",
]:
    if not (ROOT / required_path).exists():
        warnings.append(f"OPTIONAL/SETUP ASSET MISSING: {required_path}")

# 6. Never expose credential files in a source distribution.
for filename in glob.glob("**/*", recursive=True):
    path = Path(filename)
    if path.is_file() and any(part in {".git", ".venv", "venv", "__pycache__"} for part in path.parts):
        continue
    if path.name == ".env":
        warnings.append(".env exists locally; keep it private and never commit it.")

print("SMARTGOV AI PREFLIGHT")
print("=====================")
print(f"Python: {sys.version.split()[0]}")
print(f"Root:   {ROOT}")
print(f"Routes discovered: {len(routes)}")
print(f"Errors: {len(errors)}")
print(f"Warnings: {len(warnings)}")
for item in errors:
    print("ERROR:", item)
for item in warnings:
    print("WARN:", item)
if errors:
    raise SystemExit(1)
print("PREFLIGHT PASS")
