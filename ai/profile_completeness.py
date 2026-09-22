# PATH: GovScheme/ai/profile_completeness.py
"""
Profile completeness (master prompt: "DOCUMENT/PROFILE READINESS").

IMPORTANT SCOPE NOTE: this deliberately covers only PROFILE fields (age,
state, district, education, etc.) - not government DOCUMENTS (Aadhaar
card, income certificate, etc.). The master prompt's DigiLocker section
explicitly warns: "Do not mark a document as available merely because the
user has a profile field containing related information." Since this
project has no real DigiLocker integration (see README), we do not
calculate or display a "document readiness %" at all, to avoid implying a
document-level verification that isn't actually happening. This module
only ever talks about profile completeness.
"""

TRACKED_FIELDS = [
    ("full_name", "Full Name"),
    ("phone", "Phone Number"),
    ("gender", "Gender"),
    ("age", "Age"),
    ("state", "State"),
    ("district", "District"),
    ("education", "Education"),
    ("occupation", "Occupation"),
    ("annual_income", "Annual Family Income"),
    ("caste", "Caste Category"),
]


def calculate_completeness(user_row: dict) -> dict:
    filled, missing = [], []
    for field, label in TRACKED_FIELDS:
        value = user_row.get(field)
        if value is not None and str(value).strip() != "":
            filled.append(label)
        else:
            missing.append(label)

    percentage = round(len(filled) / len(TRACKED_FIELDS) * 100)
    return {"percentage": percentage, "filled": filled, "missing": missing}
