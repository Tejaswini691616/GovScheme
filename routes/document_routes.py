# PATH: GovScheme/routes/document_routes.py
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request, flash
from datetime import datetime, timedelta, timezone

from routes.auth_routes import login_required
from models.user_model import get_user_by_id
from models.db import execute
from services.document_readiness import get_readiness, connection_state, integration_status
from services.digilocker_service import create_state, build_authorization_url, exchange_code, fetch_document_metadata, sync_document_metadata, save_connection_state
from config import Config


documents_bp = Blueprint("documents", __name__)


@documents_bp.get("/documents/readiness")
@login_required
def document_readiness():
    user = get_user_by_id(session["user_id"])
    scheme_id = request.args.get("scheme_id", "").strip() or None
    scheme = None
    if scheme_id:
        from models.scheme_model import get_scheme_by_id
        scheme = get_scheme_by_id(scheme_id)
    readiness = get_readiness(user, scheme_id)
    return render_template(
        "documents/readiness.html",
        readiness=readiness,
        scheme=scheme,
        connection_status=connection_state(user["user_id"]),
        integration=integration_status(),
        digilocker_url=Config.DIGILOCKER_AUTH_URL,
    )


@documents_bp.get("/documents/digilocker/connect")
@login_required
def digilocker_connect():
    if not Config.DIGILOCKER_ENABLED:
        flash("DigiLocker live integration is not configured. Use the official DigiLocker portal directly.", "info")
        return redirect(url_for("documents.document_readiness"))
    state = create_state()
    session["digilocker_oauth_state"] = state
    session["digilocker_oauth_state_created"] = __import__("time").time()
    return redirect(build_authorization_url(state))


@documents_bp.get("/documents/digilocker/callback")
@login_required
def digilocker_callback():
    expected = session.pop("digilocker_oauth_state", None)
    session.pop("digilocker_oauth_state_created", None)
    if not expected or request.args.get("state") != expected:
        save_connection_state(session["user_id"], "PERMISSION_REQUIRED")
        return redirect(url_for("documents.document_readiness"))
    if request.args.get("error"):
        save_connection_state(session["user_id"], "PERMISSION_REQUIRED")
        return redirect(url_for("documents.document_readiness"))
    code = request.args.get("code")
    if not code:
        save_connection_state(session["user_id"], "PERMISSION_REQUIRED")
        return redirect(url_for("documents.document_readiness"))
    try:
        token_payload = exchange_code(code)
        documents = fetch_document_metadata(token_payload["access_token"])
        expires_at = None
        if token_payload.get("expires_in"):
            expires_at = (datetime.now(timezone.utc) + timedelta(seconds=int(token_payload["expires_in"]))).isoformat()
        sync_document_metadata(session["user_id"], documents, expires_at=expires_at)
        flash("DigiLocker connection completed. Only document availability metadata is retained.", "success")
    except Exception:
        save_connection_state(session["user_id"], "UNAVAILABLE")
        flash("DigiLocker document access is currently unavailable. You can access your documents directly through the official DigiLocker portal.", "warning")
    return redirect(url_for("documents.document_readiness"))


@documents_bp.post("/documents/digilocker/disconnect")
@login_required
def digilocker_disconnect():
    # We intentionally do not send guessed revocation calls. Local metadata is
    # removed and the user can revoke consent through the official provider.
    user_id = session["user_id"]
    execute("DELETE FROM document_records WHERE user_id=? AND source='DigiLocker'", (user_id,))
    execute("DELETE FROM digilocker_connections WHERE user_id=?", (user_id,))
    execute("INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)", (user_id, "DIGILOCKER_DISCONNECT", "Local DigiLocker metadata removed; provider-side revocation must use the official DigiLocker interface."))
    flash("DigiLocker connection removed from SmartGov AI. If needed, revoke provider consent through the official DigiLocker interface.", "info")
    return redirect(url_for("documents.document_readiness"))


@documents_bp.get("/api/documents/readiness")
@login_required
def document_readiness_api():
    user = get_user_by_id(session["user_id"])
    scheme_id = request.args.get("scheme_id", "").strip() or None
    return jsonify({"success": True, "scheme_id": scheme_id, "connection_status": connection_state(user["user_id"]), "integration": integration_status(), "readiness": get_readiness(user, scheme_id)})
