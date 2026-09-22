
import os
from flask import Flask, jsonify, render_template, request, session, redirect, url_for

from config import Config
from database.build_db import build_database
from models.db import query_one
from models.notification_model import unread_count


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

    # Safe/idempotent schema creation + additive migrations. Existing rows are preserved.
    with app.app_context():
        build_database()
        from database.admin_bootstrap import sync_admins
        sync_admins()

    from routes.auth_routes import auth_bp
    from routes.dashboard_routes import dashboard_bp
    from routes.scheme_routes import scheme_bp
    from routes.application_routes import application_bp
    from routes.profile_routes import profile_bp
    from routes.notification_routes import notification_bp
    from routes.admin_routes import admin_bp
    from routes.chatbot_routes import chatbot_bp
    from routes.complaint_routes import complaint_bp
    from routes.feedback_routes import feedback_bp
    from routes.settings_routes import settings_bp
    from routes.eligibility import eligibility_bp
    from routes.api import api_bp
    from routes.document_routes import documents_bp

    for bp in (auth_bp, dashboard_bp, scheme_bp, application_bp, profile_bp,
               notification_bp, admin_bp, chatbot_bp, complaint_bp, feedback_bp,
               settings_bp, eligibility_bp, api_bp, documents_bp):
        app.register_blueprint(bp)

    @app.context_processor
    def inject_globals():
        user_id = session.get("user_id")
        user = query_one("SELECT * FROM users WHERE user_id = ?", (user_id,)) if user_id else None
        return {
            "current_user": user,
            "current_user_is_admin": bool(user and user.get("is_admin")),
            "unread_notifications": unread_count(user_id) if user_id else 0,
            "disclaimer": Config.DISCLAIMER,
            "supported_languages": __import__("ai.language_service", fromlist=["get_supported_text_languages"]).get_supported_text_languages(),
            "current_language": (user.get("preferred_language") if user else request.cookies.get("sg_language", "English")),
            "theme_preference": user.get("theme_preference") if user else request.cookies.get("sg_theme", "system"),
            "text_size": user.get("text_size") if user else request.cookies.get("sg_text_size", "normal"),
            "reduced_motion": bool(user.get("reduced_motion")) if user else request.cookies.get("sg_reduced_motion") == "1",
            "digilocker_enabled": Config.DIGILOCKER_ENABLED,
            "digilocker_url": Config.DIGILOCKER_AUTH_URL,
        }

    @app.before_request
    def same_origin_protection():
        # Lightweight CSRF defense for this prototype: reject cross-origin
        # state-changing browser requests when the browser supplies Origin/Referer.
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.path not in {"/api/health"}:
            origin = request.headers.get("Origin") or request.headers.get("Referer")
            if origin:
                from urllib.parse import urlparse
                parsed = urlparse(origin)
                if parsed.netloc and parsed.netloc != request.host:
                    return jsonify(success=False, error="Cross-origin request rejected."), 403 if request.path.startswith("/api/") else 403

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    @app.errorhandler(400)
    def bad_request(e):
        if request.path.startswith("/api/"):
            return jsonify(success=False, error="Invalid request."), 400
        return render_template("errors/error.html", code=400, title="Invalid request", message="Please check the information and try again."), 400

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith("/api/"):
            return jsonify(success=False, error="Access denied."), 403
        return render_template("errors/error.html", code=403, title="Access denied", message="You don't have permission to view this page."), 403

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify(success=False, error="Resource not found."), 404
        return render_template("errors/error.html", code=404, title="Page not found", message="That page doesn't exist or may have moved."), 404

    @app.errorhandler(413)
    def too_large(e):
        if request.path.startswith("/api/"):
            return jsonify(success=False, error="Uploaded content is too large."), 413
        return render_template("errors/error.html", code=413, title="File too large", message="The uploaded file is larger than the allowed limit."), 413

    @app.errorhandler(500)
    def server_error(e):
        if request.path.startswith("/api/"):
            return jsonify(success=False, error="An unexpected server error occurred."), 500
        return render_template("errors/error.html", code=500, title="Something went wrong", message="An unexpected error occurred. Please try again."), 500

    @app.route("/")
    def index():
        return redirect(url_for("dashboard.dashboard_home")) if session.get("user_id") else redirect(url_for("auth.login"))

    # Start the scheduler only outside the debug reloader's parent process.
    if not app.testing and (not Config.DEBUG or os.environ.get("WERKZEUG_RUN_MAIN") == "true"):
        from automation.scheduler import init_scheduler
        init_scheduler(app)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=Config.DEBUG, host="127.0.0.1", port=5000)
