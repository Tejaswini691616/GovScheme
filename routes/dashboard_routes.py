# PATH: GovScheme/routes/dashboard_routes.py
from flask import Blueprint, render_template, session, request, jsonify

from routes.auth_routes import login_required
from models.user_model import get_user_by_id, citizen_dict_for_engine
from models.scheme_model import get_categories_with_counts
from models.db import query
from ai.recommendation_model import get_eligible_schemes_with_explanations
from services.recommendation_service import refresh_user_recommendations
from ai.profile_completeness import calculate_completeness
from ai.eligibility_simulator import simulate

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/help")
@login_required
def help_center():
    return render_template("help/help.html")


def _citizen_journey_steps(user, saved_count, applications_count, eligible_count, completeness_pct):
    """Master prompt: "CITIZEN JOURNEY" - a simple, honest progress model
    based on things the user has actually done, not a guess."""
    steps = [
        {"label": "Complete Profile", "done": completeness_pct >= 80},
        {"label": "Discover Schemes", "done": eligible_count > 0},
        {"label": "Check Eligibility", "done": eligible_count > 0},
        {"label": "Compare / Save", "done": saved_count > 0},
        {"label": "Apply", "done": applications_count > 0},
        {"label": "Track", "done": applications_count > 0},
        {"label": "Get Support", "done": False},
    ]
    return steps


@dashboard_bp.route("/dashboard")
@login_required
def dashboard_home():
    user = get_user_by_id(session["user_id"])
    categories = get_categories_with_counts()
    recommendations = refresh_user_recommendations(user, top_k=5)

    saved = query("""
        SELECT s.* FROM saved_schemes ss JOIN schemes s ON ss.scheme_id = s.scheme_id
        WHERE ss.user_id = ? ORDER BY ss.saved_date DESC LIMIT 6
    """, (user["user_id"],))
    saved_ids = {s["scheme_id"] for s in saved}

    total_schemes = query("SELECT COUNT(*) as c FROM schemes")[0]["c"]
    applications_count = query("SELECT COUNT(*) as c FROM applications WHERE user_id = ?",
                                (user["user_id"],))[0]["c"]

    completeness = calculate_completeness(user)
    eligible = get_eligible_schemes_with_explanations(user)
    journey = _citizen_journey_steps(user, len(saved), applications_count, len(eligible), completeness["percentage"])

    return render_template("dashboard/dashboard.html",
                            user=user, categories=categories,
                            recommendations=recommendations,
                            saved_schemes=saved, saved_ids=saved_ids,
                            total_schemes=total_schemes,
                            completeness=completeness,
                            eligible_count=len(eligible),
                            applications_count=applications_count,
                            journey=journey)


@dashboard_bp.route("/api/eligibility-simulator", methods=["POST"])
@login_required
def eligibility_simulator_api():
    """
    Read-only "what if" preview (master prompt: "ELIGIBILITY SIMULATOR").
    Never writes to the user's real profile - see ai/eligibility_simulator.py.
    """
    user = get_user_by_id(session["user_id"])
    data = request.get_json(force=True) or {}

    overrides = {}
    if "annual_income" in data and data["annual_income"] not in (None, ""):
        try:
            overrides["annual_family_income"] = float(data["annual_income"])
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid income value"}), 400
    if "age" in data and data["age"] not in (None, ""):
        try:
            overrides["age"] = float(data["age"])
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid age value"}), 400
    for flag in ["farmer", "student", "bpl", "disabled", "senior_citizen", "widow"]:
        if flag in data:
            overrides["disability" if flag == "disabled" else flag] = data[flag]

    result = simulate(user, overrides)
    return jsonify({"success": True, **result})
