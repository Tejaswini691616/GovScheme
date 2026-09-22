# PATH: GovScheme/tests/test_recommendation.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.recommendation_model import get_recommendations, get_eligible_schemes_with_explanations


def make_fake_user(**overrides):
    base = {
        "user_id": 1, "age": 35, "annual_income": 120000, "caste": "General",
        "farmer": "Yes", "bpl": "No", "disabled": "No", "student": "No",
        "senior_citizen": "No", "widow": "No", "land_holding_acres": 2,
        "gender": "Male", "state": "Karnataka",
    }
    base.update(overrides)
    return base


def test_recommendations_are_subset_of_eligible():
    user = make_fake_user()
    eligible = get_eligible_schemes_with_explanations(user)
    eligible_ids = {e["scheme"]["scheme_id"] for e in eligible}

    recs = get_recommendations(user, top_k=5)
    rec_ids = {r["scheme"]["scheme_id"] for r in recs}

    assert rec_ids.issubset(eligible_ids), "Recommendations must never include ineligible schemes"


def test_top_k_respected():
    user = make_fake_user()
    recs = get_recommendations(user, top_k=3)
    assert len(recs) <= 3


def test_recommendations_sorted_descending_by_score():
    user = make_fake_user()
    recs = get_recommendations(user, top_k=10)
    scores = [r["relevance_score"] for r in recs]
    assert scores == sorted(scores, reverse=True)
