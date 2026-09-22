# PATH: GovScheme/routes/feedback_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from routes.auth_routes import login_required
from models.feedback_model import create_feedback, VALID_FEATURES
from models.notification_model import create_notification
from models.db import query
from ai.speech_to_text import get_stt_service, SpeechToTextError

feedback_bp = Blueprint("feedback", __name__)


@feedback_bp.route("/feedback", methods=["GET", "POST"])
@login_required
def feedback_form():
    if request.method == "POST":
        form = request.form
        try:
            rating = int(form.get("rating", 0))
        except ValueError:
            rating = 0
        if rating < 1 or rating > 5:
            flash("Please select a star rating between 1 and 5.", "warning")
            return render_template("feedback/feedback.html", features=VALID_FEATURES)

        create_feedback(
            user_id=session["user_id"],
            rating=rating,
            comment=form.get("comment", "").strip(),
            language=form.get("language", "English"),
            voice_transcribed=form.get("voice_transcribed") == "1",
            feature=form.get("feature") or None,
            page=form.get("page") or None,
        )
        create_notification(session["user_id"], "Feedback received", "Thank you. Your feedback has been recorded for SmartGov AI improvement.")
        if rating <= 2:
            for admin in query("SELECT user_id FROM users WHERE is_admin=1"):
                create_notification(admin["user_id"], "Low feedback rating", f"A citizen submitted a {rating}-star rating. Review feedback analytics.")
        flash("Thank you for your feedback!", "success")
        return redirect(url_for("dashboard.dashboard_home"))

    return render_template("feedback/feedback.html", features=VALID_FEATURES)


@feedback_bp.post("/api/feedback/transcribe")
@login_required
def transcribe_feedback():
    audio = request.files.get("audio")
    language = request.form.get("language", "English")
    if not audio:
        return {"success": False, "error": "No audio provided"}, 400
    stt = get_stt_service()
    if not stt.is_available():
        return {"success": False, "error": "Voice transcription is not configured."}, 503
    try:
        return {"success": True, "text": stt.transcribe(audio.read(), language)}
    except SpeechToTextError as exc:
        return {"success": False, "error": str(exc)}, 502
