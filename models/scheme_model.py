# PATH: GovScheme/models/scheme_model.py
from models.db import query, query_one, execute


def get_all_schemes():
    """
    Citizen-facing scheme list. Deliberately EXCLUDES anything still
    pending admin review (verification_status containing "Candidate") -
    this includes both real official-API candidates and anything created
    while Demo Mode was on. Master prompt requirement: "Automated scheme
    discovery should NOT automatically present unverified data as
    official" - citizens must only ever see admin-verified schemes.
    Use get_all_schemes_including_candidates() for admin-only views.
    """
    return query("""
        SELECT * FROM schemes
        WHERE status = 'Active' AND verification_status IN ('VERIFIED_SOURCE','PROTOTYPE_DATASET','Verified (admin reviewed)','Verified (prototype dataset)')
        ORDER BY scheme_name
    """)


def get_all_schemes_including_candidates():
    """Admin-only: every scheme regardless of verification status."""
    return query("SELECT * FROM schemes ORDER BY scheme_name")


def get_scheme_by_id(scheme_id: str):
    return query_one("SELECT * FROM schemes WHERE scheme_id = ?", (scheme_id,))


def search_schemes(keyword: str = "", category: str = "", state: str = ""):
    sql = "SELECT * FROM schemes WHERE status = 'Active' AND verification_status IN ('VERIFIED_SOURCE','PROTOTYPE_DATASET','Verified (admin reviewed)','Verified (prototype dataset)')"
    params = []
    if keyword:
        sql += " AND (LOWER(scheme_name) LIKE ? OR LOWER(category) LIKE ? OR LOWER(eligibility) LIKE ?)"
        like = f"%{keyword.lower()}%"
        params += [like, like, like]
    if category:
        sql += " AND category = ?"
        params.append(category)
    if state:
        sql += " AND (state = ? OR state = 'All India')"
        params.append(state)
    sql += " ORDER BY scheme_name"
    return query(sql, tuple(params))


def get_categories_with_counts():
    return query("""
        SELECT category, COUNT(*) as scheme_count
        FROM schemes
        WHERE status = 'Active' AND verification_status IN ('VERIFIED_SOURCE','PROTOTYPE_DATASET','Verified (admin reviewed)','Verified (prototype dataset)')
        GROUP BY category
        ORDER BY category
    """)


def scheme_to_engine_dict(scheme_row: dict) -> dict:
    """The DB row already matches the field names ai/eligibility_engine.py expects."""
    return dict(scheme_row)
