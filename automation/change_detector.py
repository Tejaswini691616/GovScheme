# PATH: GovScheme/automation/change_detector.py
import json
from models.db import query_one

TRACKED_FIELDS = [
    "scheme_name", "category", "description", "benefits", "eligibility", "documents_required", "application_process",
    "official_link", "application_link", "government_department", "state", "min_age", "max_age",
    "income_limit", "caste_requirement", "farmer_required", "bpl_required", "land_limit_acres",
    "disability_required", "student_required", "widow_required",
]


def detect_change(candidate: dict) -> dict:
    existing = query_one("SELECT * FROM schemes WHERE scheme_id = ?", (candidate.get("scheme_id"),))
    if existing is None:
        return {"change_type": "NEW", "old_value": None, "new_value": json.dumps(candidate, default=str)}
    diffs = []
    for field in TRACKED_FIELDS:
        new = candidate.get(field)
        old = existing.get(field)
        if new is not None and str(old or "").strip() != str(new).strip():
            diffs.append({"field": field, "previous": old, "new": new})
    if diffs:
        return {"change_type": "UPDATED", "old_value": json.dumps({"scheme_id": candidate["scheme_id"]}),
                "new_value": json.dumps(diffs, default=str)}
    return {"change_type": "UNCHANGED", "old_value": None, "new_value": None}
