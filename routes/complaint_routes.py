# PATH: GovScheme/routes/complaint_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify

from routes.auth_routes import login_required
from models.complaint_model import (create_complaint, get_complaint, get_complaints_for_user,
                                     get_complaint_messages, add_complaint_message,
                                     update_complaint_status, VALID_CATEGORIES)
from models.application_model import get_application
from models.notification_model import create_notification

complaint_bp = Blueprint("complaint", __name__)


@complaint_bp.route("/complaints")
@login_required
def complaints_list():
    complaints = get_complaints_for_user(session["user_id"])
    return render_template("complaints/complaints.html", complaints=complaints, categories=VALID_CATEGORIES)


@complaint_bp.route("/complaints/new", methods=["GET", "POST"])
@login_required
def new_complaint():
    if request.method == "POST":
        form = request.form
        result = create_complaint(
            user_id=session["user_id"],
            category=form.get("category", "Other"),
            subject=form.get("subject", "").strip() or "No subject",
            description=form.get("description", "").strip(),
            language=form.get("language", "English"),
        )
        flash(f"Complaint {result['complaint_number']} raised. We'll get back to you soon.", "success")
        return redirect(url_for("complaint.complaint_details", complaint_id=result["complaint_id"]))
    return render_template("complaints/new_complaint.html", categories=VALID_CATEGORIES)


@complaint_bp.route("/complaints/<int:complaint_id>")
@login_required
def complaint_details(complaint_id):
    complaint = get_complaint(complaint_id)
    if not complaint or complaint["user_id"] != session["user_id"]:
        flash("Complaint not found.", "warning")
        return redirect(url_for("complaint.complaints_list"))
    messages = get_complaint_messages(complaint_id)
    return render_template("complaints/complaint_details.html", complaint=complaint, messages=messages)


@complaint_bp.route("/complaints/<int:complaint_id>/reply", methods=["POST"])
@login_required
def reply_complaint(complaint_id):
    complaint = get_complaint(complaint_id)
    if not complaint or complaint["user_id"] != session["user_id"]:
        flash("Complaint not found.", "warning")
        return redirect(url_for("complaint.complaints_list"))
    message = request.form.get("message", "").strip()
    if message:
        add_complaint_message(complaint_id, "user", session["user_id"], message)
        if complaint["status"] in ("RESOLVED", "CLOSED"):
            update_complaint_status(complaint_id, "OPEN")
    return redirect(url_for("complaint.complaint_details", complaint_id=complaint_id))


@complaint_bp.route("/complaints/<int:complaint_id>/close", methods=["POST"])
@login_required
def close_complaint(complaint_id):
    complaint = get_complaint(complaint_id)
    if not complaint or complaint["user_id"] != session["user_id"]:
        flash("Complaint not found.", "warning")
        return redirect(url_for("complaint.complaints_list"))
    update_complaint_status(complaint_id, "CLOSED")
    flash("Complaint closed. Thanks for letting us know.", "info")
    return redirect(url_for("complaint.complaint_details", complaint_id=complaint_id))


@complaint_bp.route("/api/complaints/raise-from-chat", methods=["POST"])
@login_required
def raise_from_chat():
    """
    Used by the chatbot's "Would you like me to raise this with customer
    support?" flow (master prompt: "AI CUSTOMER CARE"). The chatbot never
    creates the complaint silently - the frontend only calls this after the
    user explicitly confirms via the Yes button shown in the chat UI.
    """
    data = request.get_json(force=True) or {}
    description = (data.get("description") or "").strip()
    if not description:
        return jsonify({"success": False, "error": "Missing complaint description"}), 400

    result = create_complaint(
        user_id=session["user_id"],
        category=data.get("category", "Other"),
        subject=description[:80],
        description=description,
        language=data.get("language", "English"),
    )
    add_complaint_message(result["complaint_id"], "ai", None,
                           "This complaint was raised automatically after the Yojana Bharath "
                           "chatbot could not resolve the issue and the user confirmed escalation.")
    return jsonify({"success": True, "complaint_number": result["complaint_number"],
                    "complaint_id": result["complaint_id"]})
