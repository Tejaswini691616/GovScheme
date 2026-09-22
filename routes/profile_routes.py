# PATH: GovScheme/routes/profile_routes.py
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
import re
from routes.auth_routes import login_required
from models.user_model import get_user_by_id, update_user_profile, verify_password, change_password, change_email, change_phone
from models.db import query_one, execute
from services.recommendation_service import refresh_user_recommendations

profile_bp = Blueprint("profile", __name__)


def _audit(user_id, action, details=""):
    try:
        execute("INSERT INTO audit_logs(user_id, action, details) VALUES (?, ?, ?)", (user_id, action, details))
    except Exception:
        pass


@profile_bp.route("/profile")
@login_required
def profile_view():
    return render_template("profile/profile.html", user=get_user_by_id(session["user_id"]))


@profile_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def profile_edit():
    user = get_user_by_id(session["user_id"])
    if request.method == "POST":
        f = request.form
        update_user_profile(session["user_id"], {
            "full_name": (f.get("full_name") or "").strip(), "phone": (f.get("phone") or "").strip(),
            "gender": f.get("gender"), "age": int(f["age"]) if f.get("age") else None, "dob": f.get("dob"),
            "marital_status": f.get("marital_status"), "rural_urban": f.get("rural_urban"), "pin_code": f.get("pin_code"),
            "family_size": int(f["family_size"]) if f.get("family_size") else None, "dependents": int(f["dependents"]) if f.get("dependents") else None,
            "employment_status": f.get("employment_status"), "minority": f.get("minority"),
            "state": f.get("state"), "district": f.get("district"), "education": f.get("education"),
            "occupation": f.get("occupation"), "annual_income": int(f["annual_income"]) if f.get("annual_income") else None,
            "caste": f.get("caste"), "farmer": f.get("farmer", "No"), "student": f.get("student", "No"),
            "disabled": f.get("disabled", "No"), "disability_percentage": float(f.get("disability_percentage")) if f.get("disability_percentage") else 0,
            "senior_citizen": f.get("senior_citizen", "No"), "bpl": f.get("bpl", "No"), "widow": f.get("widow", "No"),
            "health_insurance": f.get("health_insurance"), "aadhaar": f.get("aadhaar"), "bank_account": f.get("bank_account"),
            "ration_card": f.get("ration_card"), "existing_benefits": f.get("existing_benefits"),
            "land_holding_acres": float(f.get("land_holding_acres")) if f.get("land_holding_acres") else 0,
        })
        refresh_user_recommendations(get_user_by_id(session["user_id"]), top_k=5)
        _audit(session["user_id"], "PROFILE_UPDATED")
        flash("Profile updated and recommendations refreshed.", "success")
        return redirect(url_for("profile.profile_view"))
    return render_template("profile/profile_edit.html", user=user)


@profile_bp.post("/profile/change-password")
@login_required
def change_password_route():
    user = get_user_by_id(session["user_id"])
    if not verify_password(user, request.form.get("current_password", "")):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for("profile.profile_view"))
    new = request.form.get("new_password", "")
    if len(new) < 8 or new != request.form.get("confirm_password", ""):
        flash("New passwords must match and contain at least 8 characters.", "danger")
        return redirect(url_for("profile.profile_view"))
    change_password(user["user_id"], new)
    _audit(user["user_id"], "PASSWORD_CHANGED")
    flash("Password changed successfully.", "success")
    return redirect(url_for("profile.profile_view"))


@profile_bp.post("/profile/change-email")
@login_required
def change_email_route():
    user = get_user_by_id(session["user_id"])
    if not verify_password(user, request.form.get("current_password", "")):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for("profile.profile_view"))
    new_email = (request.form.get("email") or "").strip().lower()
    if not new_email or query_one("SELECT user_id FROM users WHERE lower(email)=? AND user_id<>?", (new_email, user["user_id"])):
        flash("That email is already in use or invalid.", "danger")
        return redirect(url_for("profile.profile_view"))
    change_email(user["user_id"], new_email)
    _audit(user["user_id"], "EMAIL_CHANGED")
    flash("Email address updated.", "success")
    return redirect(url_for("profile.profile_view"))


@profile_bp.post("/profile/change-phone")
@login_required
def change_phone_route():
    user = get_user_by_id(session["user_id"])
    if not verify_password(user, request.form.get("current_password", "")):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for("profile.profile_view"))
    phone = request.form.get("phone", "").strip()
    if not re.fullmatch(r"\+?[0-9]{10,15}", re.sub(r"[\s-]", "", phone)):
        flash("Please enter a valid phone number.", "danger")
        return redirect(url_for("profile.profile_view"))
    change_phone(user["user_id"], phone)
    _audit(user["user_id"], "PHONE_CHANGED")
    flash("Phone number updated.", "success")
    return redirect(url_for("profile.profile_view"))
