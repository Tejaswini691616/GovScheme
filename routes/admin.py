"""
SmartGov AI - Admin Routes & RPA Controls

Provides administrative dashboard and execution triggers for RPA updates:
- Restricts RPA triggers to authenticated administrators.
- Bounded, controlled background thread execution so Flask never freezes.
- Displays summary statistics (Total, Successful, Unavailable, Other Errors, Last Run).
- Lists schemes with live RPA status, source portals, and last-checked timestamps.
"""

import threading
from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)
from werkzeug.security import check_password_hash
from database.db import get_db_connection

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Global background execution state
RPA_RUNNING = False
RPA_LAST_RUN_INFO = None


def background_rpa_task():
    """Executes RPA in a background worker thread."""
    global RPA_RUNNING, RPA_LAST_RUN_INFO
    RPA_RUNNING = True
    try:
        from services.rpa_service import run_rpa
        # Run headless in background so it does not interfere with the web server
        summary = run_rpa(headless=True)
        RPA_LAST_RUN_INFO = summary
    except Exception as e:
        print(f"❌ Background RPA encountered an error: {e}")
    finally:
        RPA_RUNNING = False


# ============================================================
# ADMIN AUTHENTICATION
# ============================================================

@admin_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    """Dedicated login interface for administrators."""
    if session.get("is_admin"):
        return redirect(url_for("admin.admin_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            if bool(user["is_admin"]):
                session["user_id"] = user["id"]
                session["user_name"] = user["full_name"]
                session["is_admin"] = True
                flash("Welcome to the SmartGov AI Admin Panel.", "success")
                return redirect(url_for("admin.admin_dashboard"))
            else:
                flash("Access denied: You do not have administrator permissions.", "danger")
        else:
            flash("Invalid administrator credentials.", "danger")

    return render_template("admin/login.html")


@admin_bp.route("/logout")
def admin_logout():
    """Logs out administrator and redirects to login."""
    session.pop("is_admin", None)
    flash("Administrator logged out.", "info")
    return redirect(url_for("admin.admin_login"))


# ============================================================
# ADMIN DASHBOARD & RPA MONITOR
# ============================================================

@admin_bp.route("/")
@admin_bp.route("/dashboard")
def admin_dashboard():
    """
    Renders the Government Scheme Data administration panel.
    Displays scheme statistics and provides the [RUN RPA UPDATE] control.
    """
    if not session.get("is_admin"):
        flash("Please log in as an administrator to access this area.", "warning")
        return redirect(url_for("admin.admin_login"))

    conn = get_db_connection()
    schemes = conn.execute(
        """
        SELECT
            id,
            scheme_id,
            scheme_name,
            category,
            official_url,
            source_name,
            rpa_status,
            rpa_last_checked,
            rpa_content,
            rpa_error
        FROM schemes
        ORDER BY id
        """
    ).fetchall()
    conn.close()

    total_schemes = len(schemes)
    successful = sum(1 for s in schemes if s["rpa_status"] == "SUCCESS")
    unavailable = sum(1 for s in schemes if s["rpa_status"] in ["UNAVAILABLE", "TIMEOUT", "DNS_ERROR"])
    other_errors = sum(1 for s in schemes if s["rpa_status"] in ["ALERT_ERROR", "NOT_CONFIRMED", "EMPTY_RESPONSE"])

    timestamps = [s["rpa_last_checked"] for s in schemes if s["rpa_last_checked"]]
    last_rpa_run = max(timestamps) if timestamps else "Not yet run"

    return render_template(
        "admin/dashboard.html",
        schemes=schemes,
        total_schemes=total_schemes,
        successful=successful,
        unavailable=unavailable,
        other_errors=other_errors,
        last_rpa_run=last_rpa_run,
        rpa_running=RPA_RUNNING,
        admin_name=session.get("user_name", "Administrator")
    )


# ============================================================
# TRIGGER RPA PROCESS
# ============================================================

@admin_bp.route("/run-rpa", methods=["POST"])
def run_rpa_trigger():
    """
    Controlled admin trigger for the RPA update process.
    Spawns a daemon thread so the Flask app never freezes.
    """
    global RPA_RUNNING

    if not session.get("is_admin"):
        flash("Unauthorized: Only administrators can trigger RPA updates.", "danger")
        return redirect(url_for("admin.admin_login"))

    if RPA_RUNNING:
        flash("An RPA update is already currently executing in the background.", "warning")
    else:
        worker = threading.Thread(target=background_rpa_task, daemon=True)
        worker.start()
        flash("RPA Update initiated in the background! Government scheme data is being refreshed.", "success")

    return redirect(url_for("admin.admin_dashboard"))


# ============================================================
# LIVE STATUS API (FOR DASHBOARD REFRESH)
# ============================================================

@admin_bp.route("/rpa-status")
def rpa_status():
    """Returns JSON state of the background RPA execution."""
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 403

    conn = get_db_connection()
    stats = conn.execute(
        """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN rpa_status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
            SUM(CASE WHEN rpa_status IN ('UNAVAILABLE', 'TIMEOUT', 'DNS_ERROR') THEN 1 ELSE 0 END) as unavailable,
            SUM(CASE WHEN rpa_status IN ('ALERT_ERROR', 'NOT_CONFIRMED', 'EMPTY_RESPONSE') THEN 1 ELSE 0 END) as other_errors,
            MAX(rpa_last_checked) as last_run
        FROM schemes
        """
    ).fetchone()
    conn.close()

    return jsonify({
        "running": RPA_RUNNING,
        "total": stats["total"] or 0,
        "successful": stats["successful"] or 0,
        "unavailable": stats["unavailable"] or 0,
        "other_errors": stats["other_errors"] or 0,
        "last_run": stats["last_run"] or "Not yet run"
    })
