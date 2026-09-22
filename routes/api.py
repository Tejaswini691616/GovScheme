# PATH: GovScheme/routes/api.py
from flask import Blueprint, jsonify, request, session, url_for
from routes.auth_routes import login_required, admin_required
from ai.language_service import get_supported_text_languages, voice_support_for
from ai.speech_to_text import get_stt_service
from ai.text_to_speech import get_tts_service
from config import Config
from services.semantic_search import semantic_search

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/health")
def health():
    return jsonify({"success": True, "status": "ok"})


@api_bp.get("/chat/voice/status")
def voice_status():
    return jsonify({
        "success": True,
        "stt_provider": Config.STT_PROVIDER or None,
        "tts_provider": Config.TTS_PROVIDER or None,
        "stt_available": get_stt_service().is_available(),
        "tts_languages": {
            lang: get_tts_service().is_available_for(lang) for lang in get_supported_text_languages()
        },
    })


@api_bp.get("/schemes/search")
def scheme_search_api():
    q = request.args.get("q", "").strip()
    language = request.args.get("language", "English")
    user_id = session.get("user_id")
    results = semantic_search(q, language=language, user_id=user_id, limit=10)
    return jsonify({"success": True, "results": results})


@api_bp.get("/navigation")
@login_required
def navigation_map():
    return jsonify({
        "success": True,
        "actions": {
            "dashboard": url_for("dashboard.dashboard_home"),
            "schemes": url_for("scheme.schemes_list"),
            "applications": url_for("application.applications_list"),
            "saved": url_for("scheme.saved_schemes"),
            "notifications": url_for("notification.notifications_list"),
            "profile": url_for("profile.profile_view"),
            "help": url_for("dashboard.help_center"),
            "complaints": url_for("complaint.complaints_list"),
            "feedback": url_for("feedback.feedback_form"),
        },
    })


@api_bp.get("/admin/system-health")
@admin_required
def system_health():
    from models.db import query_one
    from ai.predict import model_status
    return jsonify({"success": True, "database": bool(query_one("SELECT 1 AS ok")),
                    "model": model_status(),
                    "stt_provider": Config.STT_PROVIDER or None,
                    "tts_provider": Config.TTS_PROVIDER or None,
                    "rpa_mode": Config.RPA_MODE})
