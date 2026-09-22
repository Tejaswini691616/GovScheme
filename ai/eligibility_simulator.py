# PATH: GovScheme/ai/eligibility_simulator.py
"""
Eligibility Simulator (master prompt: "ELIGIBILITY SIMULATOR").

Lets a citizen preview "what if my income were X" / "what if I were a
farmer" WITHOUT saving anything to their profile. Reuses the exact same
eligibility engine as the real dashboard - no second implementation.
"""
from ai.eligibility_engine import evaluate_eligibility
from models.scheme_model import get_all_schemes, scheme_to_engine_dict
from models.user_model import citizen_dict_for_engine


def count_potentially_eligible(citizen: dict) -> int:
    schemes = [scheme_to_engine_dict(s) for s in get_all_schemes()]
    return sum(1 for s in schemes if evaluate_eligibility(citizen, s).is_eligible)


def simulate(user_row: dict, overrides: dict) -> dict:
    """
    overrides: a dict of citizen-engine field overrides, e.g.
        {"annual_family_income": 180000, "farmer": "Yes"}
    Returns: {"before": int, "after": int, "delta": int}
    Nothing is written to the database - this is read-only, per spec
    ("Do not save changes unless user explicitly chooses 'Update My
    Profile'").
    """
    baseline_citizen = citizen_dict_for_engine(user_row)
    simulated_citizen = dict(baseline_citizen)
    simulated_citizen.update(overrides)

    before = count_potentially_eligible(baseline_citizen)
    after = count_potentially_eligible(simulated_citizen)
    return {"before": before, "after": after, "delta": after - before}
