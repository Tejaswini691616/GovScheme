# PATH: GovScheme/routes/scheme_routes.py
from flask import Blueprint, render_template, request, session, redirect, url_for, flash

from routes.auth_routes import login_required
from models.scheme_model import search_schemes, get_scheme_by_id, get_categories_with_counts
from models.user_model import get_user_by_id
from models.db import query, execute
from ai.eligibility_engine import evaluate_eligibility
from services.semantic_search import semantic_search
from models.user_model import citizen_dict_for_engine
from models.scheme_model import scheme_to_engine_dict

scheme_bp = Blueprint("scheme", __name__)


@scheme_bp.route("/schemes")
@login_required
def schemes_list():
    keyword = request.args.get("q", "")
    category = request.args.get("category", "")
    state = request.args.get("state", "")
    # "show_all=1" opts into seeing every scheme regardless of eligibility;
    # default view only shows schemes that match the citizen's profile
    # (master prompt: "if a scheme doesn't match, don't show it to the
    # user"). Kept as an explicit opt-in toggle rather than a hard removal
    # so a citizen can still browse everything if they want to.
    show_all = request.args.get("show_all") == "1"

    results = semantic_search(keyword, language=get_user_by_id(session["user_id"]).get("preferred_language", "English"), user_id=session["user_id"], limit=50) if keyword else search_schemes(keyword="", category=category, state=state)
    if category or state:
        allowed = search_schemes(keyword="", category=category, state=state)
        allowed_ids = {r["scheme_id"] for r in allowed}
        results = [r for r in results if r["scheme_id"] in allowed_ids]
    categories = get_categories_with_counts()

    user = get_user_by_id(session["user_id"])
    citizen = citizen_dict_for_engine(user)
    filtered_results = []
    for s in results:
        result = evaluate_eligibility(citizen, scheme_to_engine_dict(s))
        s["eligibility_badge"] = "Potentially Eligible" if result.is_eligible else "Not Eligible"
        if show_all or result.is_eligible:
            filtered_results.append(s)

    saved_ids = {r["scheme_id"] for r in query(
        "SELECT scheme_id FROM saved_schemes WHERE user_id = ?", (user["user_id"],))}

    return render_template("schemes/schemes.html", schemes=filtered_results, categories=categories,
                            keyword=keyword, category=category, saved_ids=saved_ids,
                            show_all=show_all, total_matching=len(results))


@scheme_bp.route("/schemes/<scheme_id>")
@login_required
def scheme_details(scheme_id):
    scheme = get_scheme_by_id(scheme_id)
    if not scheme:
        flash("Scheme not found.", "warning")
        return redirect(url_for("scheme.schemes_list"))

    user = get_user_by_id(session["user_id"])
    citizen = citizen_dict_for_engine(user)
    result = evaluate_eligibility(citizen, scheme_to_engine_dict(scheme))

    is_saved = query("SELECT 1 FROM saved_schemes WHERE user_id = ? AND scheme_id = ?",
                      (user["user_id"], scheme_id))

    from services.document_readiness import get_readiness
    readiness = get_readiness(user, scheme_id)
    return render_template("schemes/scheme_details.html", scheme=scheme, result=result,
                            is_saved=bool(is_saved), readiness=readiness)


@scheme_bp.route("/schemes/<scheme_id>/save", methods=["POST"])
@login_required
def save_scheme(scheme_id):
    execute("INSERT OR IGNORE INTO saved_schemes (user_id, scheme_id) VALUES (?, ?)",
            (session["user_id"], scheme_id))
    flash("Scheme saved.", "success")
    return redirect(request.referrer or url_for("scheme.schemes_list"))


@scheme_bp.route("/schemes/<scheme_id>/unsave", methods=["POST"])
@login_required
def unsave_scheme(scheme_id):
    execute("DELETE FROM saved_schemes WHERE user_id = ? AND scheme_id = ?",
            (session["user_id"], scheme_id))
    flash("Scheme removed from saved list.", "info")
    return redirect(request.referrer or url_for("scheme.schemes_list"))


@scheme_bp.route("/schemes/updates")
@login_required
def scheme_updates():
    """Citizen-facing recent scheme changes. Only changes for schemes that
    are already trusted in the citizen catalogue are shown."""
    updates = query("""
        SELECT u.*, s.scheme_name
        FROM scheme_updates u
        LEFT JOIN schemes s ON s.scheme_id = u.scheme_id
        WHERE s.status = 'Active'
          AND s.verification_status IN ('VERIFIED_SOURCE','PROTOTYPE_DATASET','Verified (admin reviewed)','Verified (prototype dataset)')
        ORDER BY u.checked_at DESC
        LIMIT 50
    """)
    return render_template("schemes/updates.html", updates=updates)


@scheme_bp.route("/saved-schemes")
@login_required
def saved_schemes_list():
    schemes = query("""
        SELECT s.* FROM saved_schemes ss JOIN schemes s ON ss.scheme_id = s.scheme_id
        WHERE ss.user_id = ? ORDER BY ss.saved_date DESC
    """, (session["user_id"],))
    return render_template("schemes/saved_schemes.html", schemes=schemes)

@scheme_bp.route("/schemes/compare")
@login_required
def compare_schemes():
    ids = [x.strip() for x in request.args.get("ids", "").split(",") if x.strip()][:4]
    schemes = [get_scheme_by_id(i) for i in ids]
    schemes = [s for s in schemes if s]
    user = get_user_by_id(session["user_id"])
    citizen = citizen_dict_for_engine(user)
    evaluated = [(s, evaluate_eligibility(citizen, scheme_to_engine_dict(s))) for s in schemes]
    return render_template("eligibility/comparison.html", schemes=schemes, evaluated=evaluated)
