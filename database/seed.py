import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import pandas as pd

# Ensure project root is in sys.path so seed.py can run standalone from any directory
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = CURRENT_DIR.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from database.db import DB_PATH, SCHEMA_PATH, PROJECT_ROOT, get_db_connection

# ==========================================
# PATHS
# ==========================================

EXCEL_PATH = os.path.join(
    str(PROJECT_ROOT),
    "Dataset",
    "Government_Scheme_Eligibility_Upgraded.xlsx"
)


# ==========================================
# INITIALIZE DATABASE
# ==========================================

def initialize_database():

    conn = get_db_connection()

    try:

        with open(SCHEMA_PATH, "r", encoding="utf-8") as schema_file:

            conn.executescript(schema_file.read())

        conn.commit()

        print("✅ Database schema initialized successfully.")

    finally:

        conn.close()


# ==========================================
# CONVERT BOOLEAN VALUES
# ==========================================

def convert_boolean(value):

    if pd.isna(value):
        return 0

    if isinstance(value, bool):
        return 1 if value else 0

    value = str(value).strip().lower()

    if value in ["true", "yes", "1", "y", "required"]:
        return 1

    return 0


# ==========================================
# IMPORT SCHEME MASTER
# ==========================================

def import_schemes():

    print("\n📂 Reading government scheme dataset...")

    if not os.path.exists(EXCEL_PATH):

        print("❌ Excel dataset not found.")

        print(f"Expected location:")
        print(EXCEL_PATH)

        return

    try:

        # Read Scheme_Master sheet
        df = pd.read_excel(
            EXCEL_PATH,
            sheet_name="Scheme_Master"
        )

    except Exception as error:

        print("❌ Unable to read Excel dataset.")
        print("Error:", error)

        return


    print(f"✅ Dataset loaded successfully.")
    print(f"📊 Schemes found: {len(df)}")


    # ======================================
    # REQUIRED COLUMNS
    # ======================================

    required_columns = [

        "Scheme_ID",
        "Scheme_Name",
        "Category",
        "Min_Age",
        "Max_Age",
        "Income_Limit",
        "Caste_Requirement",
        "Farmer_Required",
        "BPL_Required",
        "Land_Limit",
        "Disability_Required",
        "Student_Required",
        "Widow_Required"

    ]


    # Check whether all required columns exist

    missing_columns = [

        column
        for column in required_columns
        if column not in df.columns

    ]


    if missing_columns:

        print("❌ Missing columns in Scheme_Master:")

        for column in missing_columns:
            print("   -", column)

        return


    conn = get_db_connection()

    try:

        inserted = 0
        skipped = 0


        # ==================================
        # INSERT EACH SCHEME
        # ==================================

        for _, row in df.iterrows():

            scheme_id = str(row["Scheme_ID"]).strip()

            scheme_name = str(row["Scheme_Name"]).strip()

            category = (
                None
                if pd.isna(row["Category"])
                else str(row["Category"]).strip()
            )


            # ------------------------------
            # Numeric values
            # ------------------------------

            min_age = (
                None
                if pd.isna(row["Min_Age"])
                else float(row["Min_Age"])
            )

            max_age = (
                None
                if pd.isna(row["Max_Age"])
                else float(row["Max_Age"])
            )

            income_limit = (
                None
                if pd.isna(row["Income_Limit"])
                else float(row["Income_Limit"])
            )


            # ------------------------------
            # Text requirement
            # ------------------------------

            caste_requirement = (

                None
                if pd.isna(row["Caste_Requirement"])

                else str(
                    row["Caste_Requirement"]
                ).strip()

            )


            # ------------------------------
            # Boolean requirements
            # ------------------------------

            farmer_required = convert_boolean(
                row["Farmer_Required"]
            )

            bpl_required = convert_boolean(
                row["BPL_Required"]
            )

            disability_required = convert_boolean(
                row["Disability_Required"]
            )

            student_required = convert_boolean(
                row["Student_Required"]
            )

            widow_required = convert_boolean(
                row["Widow_Required"]
            )


            # ------------------------------
            # Land limit
            # ------------------------------

            land_limit = (

                None
                if pd.isna(row["Land_Limit"])

                else row["Land_Limit"]

            )


            # ==================================
            # INSERT OR IGNORE
            # ==================================

            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO schemes (

                    scheme_id,
                    scheme_name,
                    category,
                    min_age,
                    max_age,
                    income_limit,
                    caste_requirement,
                    farmer_required,
                    bpl_required,
                    land_limit,
                    disability_required,
                    student_required,
                    widow_required

                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,

                (

                    scheme_id,
                    scheme_name,
                    category,
                    min_age,
                    max_age,
                    income_limit,
                    caste_requirement,
                    farmer_required,
                    bpl_required,
                    land_limit,
                    disability_required,
                    student_required,
                    widow_required

                )

            )


            if cursor.rowcount == 1:

                inserted += 1

            else:

                skipped += 1


        conn.commit()


        # ==================================
        # RESULTS
        # ==================================

        print("\n======================================")
        print("       SCHEME IMPORT COMPLETED")
        print("======================================")

        print(f"✅ Newly inserted : {inserted}")

        print(f"⏭️ Already existed : {skipped}")

        print(f"📊 Total dataset  : {len(df)}")

        print("======================================")


    except Exception as error:

        conn.rollback()

        print("\n❌ Error while importing schemes.")

        print("Error:", error)


    finally:

        conn.close()


# ==========================================
# VERIFY SCHEMES
# ==========================================

def verify_schemes():

    conn = get_db_connection()

    try:

        cursor = conn.execute(
            "SELECT COUNT(*) FROM schemes"
        )

        count = cursor.fetchone()[0]

        print("\n📊 Schemes currently stored in database:", count)


        if count > 0:

            print("\nFirst few schemes:")

            rows = conn.execute(
                """
                SELECT
                    scheme_id,
                    scheme_name,
                    category
                FROM schemes
                ORDER BY id
                LIMIT 5
                """
            ).fetchall()


            for row in rows:

                print(
                    f"  {row[0]} | "
                    f"{row[1]} | "
                    f"{row[2]}"
                )


    finally:

        conn.close()


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":

    print("\n======================================")
    print("        SMARTGOV AI DATABASE SEED")
    print("======================================")

    initialize_database()

    import_schemes()

    verify_schemes()

    print("\n✅ Seed process completed.")