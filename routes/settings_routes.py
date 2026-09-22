# PATH: GovScheme/routes/settings_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response, jsonify
from routes.auth_routes import login_required
from models.user_model import get_user_by_id
from models.db import execute
from ai.language_service import get_supported_text_languages

settings_bp = Blueprint("settings", __name__)
VALID_THEMES = ["light", "dark", "system", "indian-civic", "high-contrast"]
VALID_TEXT_SIZES = ["normal", "large"]


@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings_page():
    user = get_user_by_id(session["user_id"])
    if request.method == "POST":
        theme = request.form.get("theme_preference", "system")
        text_size = request.form.get("text_size", "normal")
        language = request.form.get("preferred_language", "English")
        reduced_motion = 1 if request.form.get("reduced_motion") == "on" else 0
        if theme not in VALID_THEMES: theme = "system"
        if text_size not in VALID_TEXT_SIZES: text_size = "normal"
        if language not in get_supported_text_languages(): language = "English"
        execute("""UPDATE users SET theme_preference=?, text_size=?, reduced_motion=?, preferred_language=? WHERE user_id=?""",
                (theme, text_size, reduced_motion, language, session["user_id"]))
        resp = make_response(redirect(url_for("settings.settings_page")))
        for key, value in (("sg_theme", theme), ("sg_text_size", text_size), ("sg_reduced_motion", str(reduced_motion)), ("sg_language", language)):
            resp.set_cookie(key, value, max_age=31536000, samesite="Lax")
        flash("Settings updated.", "success")
        return resp
    return render_template("settings/settings.html", user=user, themes=VALID_THEMES, text_sizes=VALID_TEXT_SIZES,
                           languages=get_supported_text_languages())


@settings_bp.post("/settings/language")
def set_language():
    language = request.form.get("language") or (request.get_json(silent=True) or {}).get("language")
    if language not in get_supported_text_languages():
        return jsonify(success=False, error="Unsupported language."), 422
    user_id = session.get("user_id")
    if user_id:
        execute("UPDATE users SET preferred_language=? WHERE user_id=?", (language, user_id))
    resp = jsonify(success=True, language=language)
    resp.set_cookie("sg_language", language, max_age=31536000, samesite="Lax")
    return resp
