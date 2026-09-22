import sqlite3
from pathlib import Path

# Canonical paths anchored to database directory inside GovScheme
DB_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DB_DIR.parent

DB_PATH = str(DB_DIR / "smartgov.db")
SCHEMA_PATH = str(DB_DIR / "schema.sql")


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db_connection():
    """Create and return a database connection with Row factory and PRAGMAs."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ==========================================
# SAFE SCHEMA MIGRATION / INITIALIZATION
# ==========================================

def init_db():
    """
    Create SmartGov AI database tables and safely ensure all required columns exist.
    Non-destructive: preserves existing records.
    """
    conn = get_db_connection()

    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
            schema = file.read()

        conn.executescript(schema)

        # Ensure RPA columns exist in schemes table
        cursor = conn.execute("PRAGMA table_info(schemes)")
        existing_cols = {row["name"] for row in cursor.fetchall()}

        rpa_columns = [
            ("official_url", "TEXT"),
            ("source_name", "TEXT"),
            ("rpa_status", "TEXT DEFAULT 'NOT_CHECKED'"),
            ("rpa_last_checked", "TIMESTAMP"),
            ("rpa_content", "TEXT"),
            ("rpa_error", "TEXT")
        ]

        for col_name, col_def in rpa_columns:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE schemes ADD COLUMN {col_name} {col_def}")

        conn.commit()
        print("SmartGov AI database initialized and verified successfully.")

    finally:
        conn.close()