# PATH: GovScheme/routes/admin_routes.py
import json
import os

from flask import Blueprint, render_template, redirect, url_for, flash, request

from routes.auth_routes import admin_required
from models.db import query, execute
from automation.scheduler import run_scheme_update_check
from models.complaint_model import get_all_complaints, get_complaint, add_complaint_message, update_complaint_status, VALID_STATUSES
from models.feedback_model import get_feedback_summary, get_recent_feedback
from models.notification_model import create_notification
from models.system_settings_model import get_discovery_source, get_check_interval_hours, set_setting
from config import Config

admin_bp = Blueprint("admin", __name__)


def _log_admin_action(admin_id, action_type, target_type=None, target_id=None, details=None):
    execute("""INSERT INTO admin_actions (admin_id, action_type, target_type, target_id, details)
               VALUES (?, ?, ?, ?, ?)""", (admin_id, action_type, target_type, target_id, details))


@admin_bp.route("/admin")
@admin_required
def admin_home():
    stats = {
        "total_citizens": query("SELECT COUNT(*) c FROM users")[0]["c"],
        "total_schemes": query("SELECT COUNT(*) c FROM schemes")[0]["c"],
        "verified_schemes": query("SELECT COUNT(*) c FROM schemes WHERE verification_status='VERIFIED_SOURCE'")[0]["c"],
        "candidate_schemes": query("SELECT COUNT(*) c FROM schemes WHERE verification_status='PENDING_REVIEW'")[0]["c"],
        "new_schemes": query("SELECT COUNT(*) c FROM scheme_updates WHERE change_type='NEW'")[0]["c"],
        "updated_schemes": query("SELECT COUNT(*) c FROM scheme_updates WHERE change_type='UPDATED'")[0]["c"],
        "total_applications": query("SELECT COUNT(*) c FROM applications")[0]["c"],
        "rpa_jobs": query("SELECT COUNT(*) c FROM rpa_jobs")[0]["c"],
        "open_complaints": query("SELECT COUNT(*) c FROM complaints WHERE status NOT IN ('RESOLVED','CLOSED')")[0]["c"],
        "total_complaints": query("SELECT COUNT(*) c FROM complaints")[0]["c"],
        "chat_sessions": query("SELECT COUNT(*) c FROM chat_sessions")[0]["c"],
    }
    recent_updates = query("SELECT * FROM scheme_updates ORDER BY checked_at DESC LIMIT 20")
    recent_logs = query("SELECT * FROM automation_logs ORDER BY run_at DESC LIMIT 10")
    complaints = get_all_complaints()
    feedback_summary = get_feedback_summary()
    recent_feedback = get_recent_feedback(limit=10)
    discovery_source = get_discovery_source()
    check_interval_hours = get_check_interval_hours()

    ml_metrics = None
    if os.path.exists(Config.ML_METRICS_PATH):
        with open(Config.ML_METRICS_PATH, "r", encoding="utf-8") as f:
            ml_metrics = json.load(f)

    return render_template("admin/admin_dashboard.html", stats=stats,
                            recent_updates=recent_updates, recent_logs=recent_logs,
                            ml_metrics=ml_metrics, complaints=complaints,
                            feedback_summary=feedback_summary, recent_feedback=recent_feedback,
                            complaint_statuses=VALID_STATUSES,
                            discovery_source=discovery_source,
                            check_interval_hours=check_interval_hours)


@admin_bp.route("/admin/run-scheme-check", methods=["POST"])
@admin_required
def run_scheme_check():
    from flask import session
    summary = run_scheme_update_check()
    _log_admin_action(session["user_id"], "RUN_SCHEME_UPDATE_CHECK", details=str(summary))
    if summary.get("error"):
        flash(f"Scheme update check failed: {summary['error']}", "danger")
    elif summary["source"] == "none":
        flash("No official government feed is configured, so no candidates were checked. "
              "Nothing was added or changed - this is expected, not an error.", "info")
    else:
        flash(f"Scheme update check complete: {summary}", "info")
    return redirect(url_for("admin.admin_home"))


@admin_bp.route("/admin/discovery-settings", methods=["POST"])
@admin_required
def update_discovery_settings():
    """
    Lets an admin explicitly choose the scheme-discovery source and the
    auto-refresh interval (master prompt: admin-selectable 2h/3h/etc, plus
    manual refresh; and "don't randomly generate schemes - only real
    official government changes"). Demo mode must be turned on knowingly,
    never silently defaulted to.
    """
    from flask import session
    from automation.scheduler import reschedule

    source = request.form.get("discovery_source", "none")
    if source not in ("none", "mock_demo", "official_api", "india_gov"):
        source = "none"
    set_setting("scheme_discovery_source", source)

    try:
        interval = int(request.form.get("check_interval_hours", 24))
    except ValueError:
        interval = 24
    if interval not in (2, 3, 6, 12, 24):
        interval = 24
    set_setting("scheme_check_interval_hours", str(interval))
    reschedule(interval)

    _log_admin_action(session["user_id"], "UPDATE_DISCOVERY_SETTINGS", details=f"source={source}, interval={interval}h")
    if source == "mock_demo":
        flash("Demo mode enabled: scheme checks will now use FAKE sample data for demonstration only. "
              "Remember to switch back to 'None' before treating any results as real.", "warning")
    else:
        flash(f"Discovery settings updated. Auto-refresh every {interval} hours.", "success")
    return redirect(url_for("admin.admin_home"))


@admin_bp.route("/admin/verify-scheme/<scheme_id>", methods=["POST"])
@admin_required
def verify_scheme(scheme_id):
    from flask import session
    scheme = query("SELECT * FROM schemes WHERE scheme_id=?", (scheme_id,))
    if not scheme:
        flash("Scheme not found.", "warning")
        return redirect(url_for("admin.admin_home"))
    scheme = scheme[0]
    from automation.scheduler import approve_latest_candidate
    approved_update = approve_latest_candidate(scheme_id, session["user_id"])
    if not approved_update:
        execute("UPDATE schemes SET verification_status = 'Verified (admin reviewed)', last_verified=datetime('now') WHERE scheme_id = ?",
                (scheme_id,))
    scheme = query("SELECT * FROM schemes WHERE scheme_id=?", (scheme_id,))[0]
    # A document requirement is trusted only after an admin has reviewed the
    # source-derived value. Never synthesize requirements from profile fields.
    requirements = []
    raw_docs = scheme.get("documents_required")
    if raw_docs:
        try:
            parsed = json.loads(raw_docs) if isinstance(raw_docs, str) and raw_docs.strip().startswith(("[", "{")) else None
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            requirements = parsed
        elif isinstance(parsed, dict):
            requirements = [parsed]
        elif isinstance(raw_docs, str):
            requirements = [part.strip() for part in raw_docs.replace("\r", "").split("\n") if part.strip()]
    if requirements and scheme.get("source_url"):
        from services.document_readiness import record_verified_scheme_requirements
        record_verified_scheme_requirements(scheme_id, scheme["source_url"], scheme.get("source_name"), requirements)
    _log_admin_action(session["user_id"], "VERIFY_SCHEME", "scheme", scheme_id,
                       f"source={scheme.get('source_url')}; document_requirements_reviewed={bool(requirements)}")
    flash(f"Scheme {scheme_id} marked as verified. Document requirements are available only when source-derived requirements were present and reviewed.", "success")
    return redirect(url_for("admin.admin_home"))


@admin_bp.route("/admin/reject-scheme/<scheme_id>", methods=["POST"])
@admin_required
def reject_scheme(scheme_id):
    from flask import session
    scheme = query("SELECT * FROM schemes WHERE scheme_id=?", (scheme_id,))
    if not scheme:
        flash("Scheme not found.", "warning")
        return redirect(url_for("admin.schemes_admin"))
    row = scheme[0]
    execute("UPDATE schemes SET verification_status='REJECTED', status='Inactive', last_updated=datetime('now') WHERE scheme_id=?", (scheme_id,))
    _log_admin_action(session["user_id"], "REJECT_SCHEME", "scheme", scheme_id, f"source={row.get('source_url')}")
    flash(f"Scheme {scheme_id} rejected and hidden from citizens.", "info")
    return redirect(url_for("admin.schemes_admin"))


@admin_bp.route("/admin/complaints/<int:complaint_id>/respond", methods=["POST"])
@admin_required
def respond_complaint(complaint_id):
    from flask import session
    complaint = get_complaint(complaint_id)
    if not complaint:
        flash("Complaint not found.", "warning")
        return redirect(url_for("admin.admin_home"))

    message = request.form.get("message", "").strip()
    new_status = request.form.get("status", complaint["status"])
    if message:
        add_complaint_message(complaint_id, "admin", session["user_id"], message)
    update_complaint_status(complaint_id, new_status, assigned_admin=session["user_id"])
    _log_admin_action(session["user_id"], "RESPOND_COMPLAINT", "complaint", complaint["complaint_number"],
                       f"status -> {new_status}")

    create_notification(complaint["user_id"], f"Update on complaint {complaint['complaint_number']}",
                         message or f"Your complaint status changed to {new_status}.")
    flash(f"Response sent for {complaint['complaint_number']}.", "success")
    return redirect(url_for("admin.admin_home"))

@admin_bp.get("/admin/users")
@admin_required
def users_admin():
    return render_template("admin/users.html", users=query("SELECT user_id,full_name,email,phone,is_admin,preferred_language,created_at FROM users ORDER BY created_at DESC"))

@admin_bp.get("/admin/schemes")
@admin_required
def schemes_admin():
    return render_template("admin/manage_schemes.html", schemes=query("SELECT * FROM schemes ORDER BY last_updated DESC, scheme_name"))

@admin_bp.get("/admin/logs")
@admin_required
def logs_admin():
    return render_template("admin/logs.html", logs=query("SELECT * FROM automation_logs ORDER BY run_at DESC LIMIT 100"), audit_logs=query("SELECT * FROM admin_actions ORDER BY created_at DESC LIMIT 100"))

@admin_bp.get("/admin/analytics")
@admin_required
def analytics_admin():
    return render_template("admin/analytics.html", feedback_summary=get_feedback_summary(), stats={
        "users": query("SELECT COUNT(*) c FROM users")[0]["c"],
        "schemes": query("SELECT COUNT(*) c FROM schemes")[0]["c"],
        "applications": query("SELECT COUNT(*) c FROM applications")[0]["c"],
        "complaints": query("SELECT COUNT(*) c FROM complaints")[0]["c"],
        "chat_sessions": query("SELECT COUNT(*) c FROM chat_sessions")[0]["c"],
    })

@admin_bp.get("/admin/rpa")
@admin_required
def rpa_admin():
    return render_template("admin/rpa_monitor.html", jobs=query("SELECT r.*,a.scheme_id FROM rpa_jobs r JOIN applications a ON a.application_id=r.application_id ORDER BY r.rpa_job_id DESC LIMIT 100"))
