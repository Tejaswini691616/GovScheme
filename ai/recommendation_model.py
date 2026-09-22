# PATH: GovScheme/ai/recommendation_model.py
"""
Shared recommendation service.

Flow (per project spec, section 21):
    Citizen Profile -> Eligibility Engine -> Potentially Eligible Schemes
    -> ML Model -> Relevance Score -> Ranking -> Top-K schemes

IMPORTANT: this is the ONLY recommendation algorithm in the project.
Both routes/dashboard_routes.py and ai/chatbot.py call get_recommendations()
so the dashboard and the chatbot are always consistent (spec section 39).
"""
from ai.eligibility_engine import evaluate_all_schemes
from ai.predict import score_schemes
from models.user_model import citizen_dict_for_engine
from models.scheme_model import get_all_schemes, scheme_to_engine_dict


def get_eligible_schemes_with_explanations(user_row: dict):
    """Returns list of dicts: {scheme, result} for schemes the rule engine
    marks as potentially eligible."""
    citizen = citizen_dict_for_engine(user_row)
    schemes = [scheme_to_engine_dict(s) for s in get_all_schemes()]
    results = evaluate_all_schemes(citizen, schemes)

    eligible = []
    for scheme, result in zip(schemes, results):
        if result.is_eligible:
            eligible.append({"scheme": scheme, "result": result})
    return eligible


def get_all_eligibility_results(user_row: dict):
    """Returns eligibility results (eligible AND not eligible) for every scheme."""
    citizen = citizen_dict_for_engine(user_row)
    schemes = [scheme_to_engine_dict(s) for s in get_all_schemes()]
    results = evaluate_all_schemes(citizen, schemes)
    return list(zip(schemes, results))


def get_recommendations(user_row: dict, top_k: int = 5):
    """
    Returns a ranked list of up to top_k dicts:
        {scheme, result (EligibilityResult), relevance_score}
    Only potentially-eligible schemes are ever recommended (spec section 21).
    """
    eligible = get_eligible_schemes_with_explanations(user_row)
    if not eligible:
        return []

    scheme_rows = [e["scheme"] for e in eligible]
    scored = score_schemes(user_row, scheme_rows)  # sorted desc by relevance

    score_by_id = {s["scheme_id"]: score for s, score in scored}
    eligible.sort(key=lambda e: score_by_id.get(e["scheme"]["scheme_id"], 0), reverse=True)

    ranked = []
    for e in eligible[:top_k]:
        ranked.append({
            "scheme": e["scheme"],
            "result": e["result"],
            "relevance_score": round(score_by_id.get(e["scheme"]["scheme_id"], 0) * 100, 1),
        })
    return ranked
