# PATH: GovScheme/routes/auth_routes.py
from datetime import datetime, timedelta, timezone
from functools import wraps
import secrets
import re

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash

from models.user_model import create_user, get_user_by_email, verify_password
from models.db import query_one
from utils.email_service import send_otp_email
from models.db import execute

def _audit(user_id, action, details=""):
    try:
        execute("INSERT INTO audit_logs(user_id, action, details) VALUES (?, ?, ?)", (user_id, action, details))
    except Exception:
        pass


auth_bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login", next=request.path))
        user = query_one("SELECT is_admin FROM users WHERE user_id = ?", (session["user_id"],))
        if not user or not user["is_admin"]:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def _valid_email(email):
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", (email or "").strip()))


def _valid_phone(phone):
    value = re.sub(r"[\s-]", "", phone or "")
    return bool(re.fullmatch(r"\+?[0-9]{10,15}", value))


def _safe_int(value, default=None):
    try:
        return int(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        form = request.form
        if (form.get("password") or "") != (form.get("confirm_password") or form.get("password") or ""):
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")
        email = (form.get("email") or "").strip().lower()
        password = form.get("password") or ""
        phone = (form.get("phone") or "").strip()
        if not _valid_email(email):
            flash("Please enter a valid email address.", "danger")
            return render_template("auth/register.html")
        if phone and not _valid_phone(phone):
            flash("Please enter a valid phone number.", "danger")
            return render_template("auth/register.html")
        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return render_template("auth/register.html")
        if get_user_by_email(email):
            flash("An account with this email already exists.", "danger")
            return render_template("auth/register.html")
        try:
            user_id = create_user({
                "full_name": (form.get("full_name") or "").strip(), "email": email,
                "password": password, "phone": (form.get("phone") or "").strip(),
                "gender": form.get("gender"), "age": _safe_int(form.get("age")),
                "state": form.get("state"), "district": form.get("district"),
                "education": form.get("education"), "occupation": form.get("occupation"),
                "annual_income": _safe_int(form.get("annual_income")), "caste": form.get("caste"),
                "farmer": form.get("farmer", "No"), "student": form.get("student", "No"),
                "disabled": form.get("disabled", "No"), "senior_citizen": form.get("senior_citizen", "No"),
                "bpl": form.get("bpl", "No"), "widow": form.get("widow", "No"),
                "land_holding_acres": float(form.get("land_holding_acres")) if form.get("land_holding_acres") else 0,
            })
        except Exception:
            flash("We could not create the account. Check the details and try again.", "danger")
            return render_template("auth/register.html")
        session.clear(); session["user_id"] = user_id
        return redirect(url_for("dashboard.dashboard_home"))
    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = get_user_by_email(email)
        if user and verify_password(user, password):
            session.clear()
            session["user_id"] = user["user_id"]
            session["user_name"] = user["full_name"]
            _audit(user["user_id"], "LOGIN_SUCCESS")
            next_url = request.form.get("next") or request.args.get("next")
            return redirect(next_url if next_url and next_url.startswith("/") else url_for("dashboard.dashboard_home"))
        _audit(user["user_id"] if user else None, "LOGIN_FAILURE")
        flash("Invalid email or password.", "danger")
    return render_template("auth/login.html", next=request.args.get("next", ""))


@auth_bp.route("/logout")
def logout():
    _audit(session.get("user_id"), "LOGOUT")
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        last_request = float(session.get("reset_last_request", 0) or 0)
        if datetime.now(timezone.utc).timestamp() - last_request < 60:
            flash("Please wait before requesting another reset code.", "warning")
            return render_template("authentication/forgot_password.html")
        session["reset_last_request"] = datetime.now(timezone.utc).timestamp()
        user = get_user_by_email(email)
        if user:
            otp = f"{secrets.randbelow(1_000_000):06d}"
            session["reset_email"] = email
            session["reset_otp_hash"] = generate_password_hash(otp)
            session["reset_otp_expires"] = (datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()
            session["reset_otp_attempts"] = 0
            try:
                sent = send_otp_email(email, otp)
            except Exception:
                sent = False
            if sent:
                _audit(user["user_id"], "PASSWORD_RESET_REQUESTED")
                flash("OTP sent to your email.", "info")
                return redirect(url_for("auth.otp_verification"))
            # Development-only fallback: never show the OTP in normal UI.
            # The code is printed to the developer console only when DEBUG is enabled.
            from config import Config
            if Config.DEBUG:
                print(f"[DEV PASSWORD RESET] OTP for {email}: {otp}")
                _audit(user["user_id"], "PASSWORD_RESET_REQUESTED_DEV")
                flash("Development reset mode: OTP was printed to the server console.", "warning")
                return redirect(url_for("auth.otp_verification"))
            flash("Password reset email is not configured on this deployment.", "warning")
        else:
            flash("If the account exists, password reset instructions can be requested for it.", "info")
    return render_template("authentication/forgot_password.html")


@auth_bp.route("/otp-verification", methods=["GET", "POST"])
def otp_verification():
    if request.method == "POST":
        from werkzeug.security import check_password_hash
        expires = session.get("reset_otp_expires", 0)
        if expires < datetime.now(timezone.utc).timestamp() or not session.get("reset_otp_hash"):
            flash("OTP expired. Please request a new one.", "danger")
            return redirect(url_for("auth.forgot_password"))
        attempts = int(session.get("reset_otp_attempts", 0))
        if attempts >= 5:
            session.pop("reset_otp_hash", None)
            session.pop("reset_otp_expires", None)
            session.pop("reset_otp_attempts", None)
            flash("Too many invalid OTP attempts. Please request a new OTP.", "danger")
            return redirect(url_for("auth.forgot_password"))
        if check_password_hash(session["reset_otp_hash"], request.form.get("otp", "")):
            session["reset_verified"] = True
            session.pop("reset_otp_attempts", None)
            session.pop("reset_otp_hash", None)
            session.pop("reset_otp_expires", None)
            _audit(query_one("SELECT user_id FROM users WHERE email=?", (session["reset_email"],))["user_id"], "PASSWORD_RESET_OTP_VERIFIED")
            return redirect(url_for("auth.reset_password"))
        session["reset_otp_attempts"] = attempts + 1
        flash("Invalid OTP.", "danger")
    return render_template("authentication/otp_verification.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if not session.get("reset_verified") or not session.get("reset_email"):
        return redirect(url_for("auth.forgot_password"))
    if request.method == "POST":
        password = request.form.get("password", "")
        if len(password) < 8 or password != request.form.get("confirm_password", ""):
            flash("Passwords must match and contain at least 8 characters.", "danger")
            return render_template("authentication/reset_password.html")
        from models.db import execute
        execute("UPDATE users SET password_hash = ? WHERE email = ?", (generate_password_hash(password), session["reset_email"]))
        reset_user = query_one("SELECT user_id FROM users WHERE email=?", (session["reset_email"],))
        _audit(reset_user["user_id"] if reset_user else None, "PASSWORD_RESET_COMPLETED")
        session.pop("reset_email", None); session.pop("reset_verified", None)
        flash("Password updated successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("authentication/reset_password.html")
