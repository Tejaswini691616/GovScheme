# PATH: GovScheme/database/build_db.py
"""Idempotent, additive SmartGov AI database builder."""
import hashlib
import os
import sqlite3
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

OFFICIAL_LINKS = {
    "S001": ("PM-KISAN", "https://pmkisan.gov.in/"),
    "S002": ("Ayushman Bharat PM-JAY", "https://pmjay.gov.in/"),
    "S004": ("National Scholarship Portal", "https://scholarships.gov.in/"),
    "S005": ("National Scholarship Portal", "https://scholarships.gov.in/"),
    "S006": ("National Scholarship Portal", "https://scholarships.gov.in/"),
    "S007": ("National Social Assistance Programme", "https://nsap.nic.in/"),
    "S009": ("PMAY-G", "https://pmayg.nic.in/"),
    "S010": ("MUDRA", "https://www.mudra.org.in/"),
    "S012": ("National Portal for Social Security Schemes", "https://jansuraksha.gov.in/"),
    "S013": ("National Portal for Social Security Schemes", "https://jansuraksha.gov.in/"),
    "S014": ("National Portal for Social Security Schemes", "https://jansuraksha.gov.in/"),
    "S015": ("PM Ujjwala Yojana", "https://www.pmuy.gov.in/"),
    "S016": ("PM SVANidhi", "https://pmsvanidhi.mohua.gov.in/"),
    "S017": ("PM Vishwakarma", "https://pmvishwakarma.gov.in/"),
    "S018": ("Stand-Up India", "https://www.standupmitra.in/"),
    "S019": ("National Scholarship Portal", "https://scholarships.gov.in/"),
    "S020": ("National Social Assistance Programme", "https://nsap.nic.in/"),
}


def _bool(v):
    if pd.isna(v):
        return 0
    return int(str(v).strip().lower() in {"1", "true", "yes", "y", "on"})


def _additive_migrations(conn):
    migrations = {
        "users": {
            "phone": "TEXT", "dob":"TEXT", "marital_status":"TEXT", "rural_urban":"TEXT", "pin_code":"TEXT",
            "family_size":"INTEGER", "dependents":"INTEGER", "employment_status":"TEXT", "minority":"TEXT",
            "disability_percentage":"REAL", "health_insurance":"TEXT", "aadhaar":"TEXT", "bank_account":"TEXT",
            "ration_card":"TEXT", "existing_benefits":"TEXT", "is_admin": "INTEGER DEFAULT 0",
            "preferred_language": "TEXT DEFAULT 'English'", "theme_preference": "TEXT DEFAULT 'light'",
            "text_size": "TEXT DEFAULT 'normal'", "reduced_motion": "INTEGER DEFAULT 0",
        },
        "schemes": {
            "source_name": "TEXT", "government_department": "TEXT", "last_verified": "TEXT", "source_hash": "TEXT",
            "application_process": "TEXT",
        },
        "applications": {"remarks": "TEXT", "created_at": "TEXT", "updated_at": "TEXT"},
        "scheme_updates": {"candidate_payload": "TEXT"},
    }
    for table, cols in migrations.items():
        existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        if not existing and table == "applications":
            continue
        for col, definition in cols.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
    conn.commit()


def _create_missing_tables(conn):
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    _additive_migrations(conn)


def build_database():
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        _create_missing_tables(conn)
        if not os.path.exists(Config.EXCEL_SOURCE_PATH):
            print(f"WARNING: Excel source not found: {Config.EXCEL_SOURCE_PATH}")
            return

        sm = pd.read_excel(Config.EXCEL_SOURCE_PATH, sheet_name="Scheme_Master")
        for _, row in sm.iterrows():
            sid = str(row["Scheme_ID"]).strip()
            name = str(row["Scheme_Name"]).strip()
            category = str(row["Category"]).strip() if pd.notna(row["Category"]) else None
            official = OFFICIAL_LINKS.get(sid)
            source_name = official[0] if official else "Prototype dataset"
            official_url = official[1] if official else None
            eligibility_parts = []
            for label, col in (("Minimum age", "Min_Age"), ("Maximum age", "Max_Age"), ("Annual income limit", "Income_Limit")):
                if pd.notna(row[col]):
                    value = int(float(row[col]))
                    eligibility_parts.append(f"{label}: ₹{value:,}" if "income" in label.lower() else f"{label}: {value}")
            for label, col in (("Caste requirement", "Caste_Requirement"),):
                if pd.notna(row[col]) and str(row[col]).strip(): eligibility_parts.append(f"{label}: {str(row[col]).strip()}")
            for label, col in (("Farmer", "Farmer_Required"), ("BPL", "BPL_Required"), ("Disability", "Disability_Required"), ("Student", "Student_Required"), ("Widow", "Widow_Required")):
                if _bool(row[col]): eligibility_parts.append(f"{label}: required")
            eligibility = "; ".join(eligibility_parts) or "No specific configured criteria."
            source_hash = hashlib.sha256((sid + "|" + name + "|" + eligibility).encode()).hexdigest()
            verification = "VERIFIED_SOURCE" if official_url else "PROTOTYPE_DATASET"
            conn.execute("""
                INSERT INTO schemes (
                    scheme_id, scheme_name, category, description, benefits, eligibility,
                    documents_required, application_process, official_link, application_link, state, status,
                    source_url, source_name, government_department, last_checked, last_updated,
                    last_verified, source_hash, verification_status, min_age, max_age, income_limit,
                    caste_requirement, farmer_required, bpl_required, land_limit_required,
                    land_limit_acres, disability_required, student_required, widow_required
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(scheme_id) DO UPDATE SET
                    scheme_name=excluded.scheme_name, category=excluded.category,
                    eligibility=excluded.eligibility, official_link=excluded.official_link,
                    application_link=excluded.application_link, source_name=excluded.source_name,
                    source_hash=excluded.source_hash, last_checked=datetime('now'), last_updated=datetime('now')
                WHERE schemes.verification_status NOT IN ('VERIFIED_SOURCE','Verified (admin reviewed)')
            """, (
                sid, name, category,
                f"{name} is included in the SmartGov AI prototype catalogue.", None, eligibility,
                None, None, official_url, official_url, "All India", "Active", official_url or "local dataset",
                source_name, None, None, None, None, source_hash, verification,
                float(row["Min_Age"]) if pd.notna(row["Min_Age"]) else None,
                float(row["Max_Age"]) if pd.notna(row["Max_Age"]) else None,
                float(row["Income_Limit"]) if pd.notna(row["Income_Limit"]) else None,
                str(row["Caste_Requirement"]).strip() if pd.notna(row["Caste_Requirement"]) else None,
                _bool(row["Farmer_Required"]), _bool(row["BPL_Required"]), _bool(row["Land_Limit"]), None,
                _bool(row["Disability_Required"]), _bool(row["Student_Required"]), _bool(row["Widow_Required"]),
            ))
        conn.commit()
        print(f"Database ready: {Config.DATABASE_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    build_database()
