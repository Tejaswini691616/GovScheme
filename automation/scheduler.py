# PATH: GovScheme/automation/scheduler.py
"""24-hour scheme discovery, change detection and post-verification refresh."""
import json
import threading

from models.db import execute, query
from models.notification_model import create_notification
from automation.scheme_scraper import fetch_candidate_schemes, SchemeDiscoveryError
from automation.change_detector import detect_change

_thread = None
_stop = threading.Event()
_interval_hours = 24


def _candidate_source(candidate):
    return "DEMO DATA" if candidate.get("_demo_data") else candidate.get("source_url", "OFFICIAL SOURCE")


def _insert_update(candidate, change, source):
    execute(
        """INSERT INTO scheme_updates(scheme_id,source,change_type,old_value,new_value,candidate_payload)
           VALUES(?,?,?,?,?,?)""",
        (candidate.get("scheme_id"), source, change["change_type"], change.get("old_value"),
         change.get("new_value"), json.dumps(candidate, default=str)),
    )


def _apply_new_candidate(candidate, source):
    execute("""INSERT OR IGNORE INTO schemes
        (scheme_id,scheme_name,category,description,benefits,eligibility,documents_required,application_process,
         official_link,application_link,state,status,source_url,source_name,government_department,
         verification_status,min_age,max_age,income_limit,caste_requirement,farmer_required,bpl_required,
         land_limit_acres,disability_required,student_required,widow_required,last_checked,last_updated)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))""",
        (candidate.get("scheme_id"),candidate.get("scheme_name"),candidate.get("category"),candidate.get("description"),
         candidate.get("benefits"),candidate.get("eligibility"),candidate.get("documents_required"),candidate.get("application_process"),candidate.get("official_link"),
         candidate.get("application_link"),candidate.get("state","All India"),"Active",candidate.get("source_url",source),
         candidate.get("source_name",source),candidate.get("government_department"),"PENDING_REVIEW",candidate.get("min_age"),
         candidate.get("max_age"),candidate.get("income_limit"),candidate.get("caste_requirement"),int(bool(candidate.get("farmer_required"))),
         int(bool(candidate.get("bpl_required"))),candidate.get("land_limit_acres"),int(bool(candidate.get("disability_required"))),
         int(bool(candidate.get("student_required"))),int(bool(candidate.get("widow_required"))))
    )


def _apply_verified_candidate(scheme_id, candidate):
    fields = [f for f in candidate if f in {
        "scheme_name","category","description","benefits","eligibility","documents_required","application_process","official_link","application_link",
        "state","source_url","source_name","government_department","min_age","max_age","income_limit","caste_requirement",
        "farmer_required","bpl_required","land_limit_acres","disability_required","student_required","widow_required"}]
    if fields:
        sets = ",".join(f"{f}=?" for f in fields)
        execute(f"UPDATE schemes SET {sets}, last_checked=datetime('now'), last_updated=datetime('now'), verification_status='VERIFIED_SOURCE', last_verified=datetime('now') WHERE scheme_id=?",
                tuple(candidate[f] for f in fields) + (scheme_id,))


def _re_evaluate_scheme(scheme_id, scheme_name):
    from ai.eligibility_engine import evaluate_eligibility
    from models.user_model import get_user_by_id, citizen_dict_for_engine
    scheme = query("SELECT * FROM schemes WHERE scheme_id=?", (scheme_id,))
    if not scheme:
        return
    scheme = scheme[0]
    for user_ref in query("SELECT user_id FROM users"):
        user = get_user_by_id(user_ref["user_id"])
        result = evaluate_eligibility(citizen_dict_for_engine(user), scheme)
        previous = query("SELECT is_eligible FROM eligibility_results WHERE user_id=? AND scheme_id=?", (user["user_id"], scheme_id))
        old = bool(previous[0]["is_eligible"]) if previous else None
        execute("""INSERT INTO eligibility_results(user_id,scheme_id,is_eligible,explanation,evaluated_at)
                   VALUES(?,?,?,?,datetime('now'))
                   ON CONFLICT(user_id,scheme_id) DO UPDATE SET is_eligible=excluded.is_eligible,
                     explanation=excluded.explanation,evaluated_at=datetime('now')""",
                (user["user_id"], scheme_id, int(result.is_eligible), result.explanation_text()))
        if old is None or old != result.is_eligible:
            create_notification(user["user_id"], "Your scheme match may have changed",
                                f"{scheme_name} was verified with updated information and your configured eligibility result changed. Please verify the official source.")
        from services.recommendation_service import refresh_user_recommendations
        refresh_user_recommendations(user, top_k=5)


def _apply_candidate(candidate):
    change = detect_change(candidate)
    source = _candidate_source(candidate)
    if change["change_type"] == "NEW":
        _apply_new_candidate(candidate, source)
        _insert_update(candidate, change, source)
    elif change["change_type"] == "UPDATED":
        # Do not overwrite trusted scheme data. Store the full source payload as
        # a pending candidate until an admin reviews it.
        _insert_update(candidate, change, source)
    else:
        _insert_update(candidate, change, source)
    return change


def _mark_missing_as_outdated(candidates, source):
    """Mark missing records only when the configured feed is a complete catalogue."""
    from config import Config
    if not Config.OFFICIAL_SCHEME_FEED_IS_COMPLETE or source not in {"official_api", "india_gov"}:
        return 0
    incoming = {c.get("scheme_id") for c in candidates if c.get("scheme_id")}
    existing = query("SELECT scheme_id,scheme_name FROM schemes WHERE status='Active' AND verification_status='VERIFIED_SOURCE'")
    count = 0
    for row in existing:
        if row["scheme_id"] not in incoming:
            execute("UPDATE schemes SET status='Inactive', verification_status='OUTDATED', last_updated=datetime('now') WHERE scheme_id=?", (row["scheme_id"],))
            execute("INSERT INTO scheme_updates(scheme_id,source,change_type,old_value,new_value,candidate_payload) VALUES(?,?,?,?,?,?)",
                    (row["scheme_id"], source, "OUTDATED", row["scheme_name"], None, None))
            count += 1
    return count


def run_scheme_update_check():
    from models.system_settings_model import get_discovery_source
    source = get_discovery_source()
    summary = {"source": source, "new": 0, "updated": 0, "unchanged": 0, "outdated": 0}
    try:
        candidates = fetch_candidate_schemes()
        for candidate in candidates:
            change = _apply_candidate(candidate)
            summary[change["change_type"].lower()] += 1
        summary["outdated"] = _mark_missing_as_outdated(candidates, source)
        execute("INSERT INTO automation_logs(job_name,status,details) VALUES(?,?,?)", ("scheme_update_check", "SUCCESS", str(summary)))
    except SchemeDiscoveryError as exc:
        summary["error"] = str(exc)
        execute("INSERT INTO automation_logs(job_name,status,details) VALUES(?,?,?)", ("scheme_update_check", "ERROR", str(exc)))
    return summary


def approve_latest_candidate(scheme_id, admin_id):
    """Apply the latest pending candidate after explicit admin review."""
    row = query("SELECT * FROM scheme_updates WHERE scheme_id=? AND change_type='UPDATED' ORDER BY update_id DESC LIMIT 1", (scheme_id,))
    if not row or not row[0].get("candidate_payload"):
        return False
    candidate = json.loads(row[0]["candidate_payload"])
    _apply_verified_candidate(scheme_id, candidate)
    execute("INSERT INTO admin_actions(admin_id,action_type,target_type,target_id,details) VALUES(?,?,?,?,?)",
            (admin_id, "APPROVE_SCHEME_UPDATE", "scheme", scheme_id, "Latest pending source candidate approved."))
    _re_evaluate_scheme(scheme_id, candidate.get("scheme_name", scheme_id))
    return True


def init_scheduler(app=None):
    global _thread
    if _thread and _thread.is_alive(): return
    _stop.clear(); _thread = threading.Thread(target=_loop, daemon=True, name="smartgov-scheme-scheduler"); _thread.start()


def reschedule(interval_hours=24):
    global _interval_hours
    _interval_hours = max(1, int(interval_hours))


def _loop():
    while not _stop.wait(_interval_hours * 3600):
        run_scheme_update_check()
