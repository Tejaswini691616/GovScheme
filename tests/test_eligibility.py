# PATH: GovScheme/tests/test_eligibility.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai.eligibility_engine import evaluate_eligibility


def make_scheme(**overrides):
    base = {
        "scheme_id": "S999", "scheme_name": "Test Scheme",
        "min_age": None, "max_age": None, "income_limit": None,
        "caste_requirement": None, "farmer_required": 0, "bpl_required": 0,
        "disability_required": 0, "student_required": 0, "widow_required": 0,
        "land_limit_required": 0, "land_limit_acres": None,
    }
    base.update(overrides)
    return base


def test_no_criteria_configured_is_not_eligible():
    scheme = make_scheme()
    citizen = {"age": 30}
    result = evaluate_eligibility(citizen, scheme)
    assert result.criteria_evaluated == 0
    assert result.is_eligible is False


def test_age_range_pass():
    scheme = make_scheme(min_age=18, max_age=60)
    citizen = {"age": 30}
    result = evaluate_eligibility(citizen, scheme)
    assert result.is_eligible is True
    assert result.criteria_evaluated == 2


def test_age_range_fail_below_min():
    scheme = make_scheme(min_age=18)
    citizen = {"age": 16}
    result = evaluate_eligibility(citizen, scheme)
    assert result.is_eligible is False
    assert len(result.failed) == 1


def test_income_limit():
    scheme = make_scheme(income_limit=200000)
    citizen = {"annual_family_income": 150000}
    assert evaluate_eligibility(citizen, scheme).is_eligible is True

    citizen2 = {"annual_family_income": 250000}
    assert evaluate_eligibility(citizen2, scheme).is_eligible is False


def test_farmer_required_yes_no_variants():
    scheme = make_scheme(farmer_required=1)
    for val in ["Yes", "yes", "YES", " Yes ", True, 1]:
        citizen = {"farmer": val}
        assert evaluate_eligibility(citizen, scheme).is_eligible is True, f"failed for {val!r}"
    for val in ["No", "no", False, 0, None, ""]:
        citizen = {"farmer": val}
        assert evaluate_eligibility(citizen, scheme).is_eligible is False, f"failed for {val!r}"


def test_caste_requirement_slash_list():
    scheme = make_scheme(caste_requirement="SC/ST")
    assert evaluate_eligibility({"caste": "SC"}, scheme).is_eligible is True
    assert evaluate_eligibility({"caste": "ST"}, scheme).is_eligible is True
    assert evaluate_eligibility({"caste": "OBC"}, scheme).is_eligible is False


def test_combined_criteria_all_must_pass():
    scheme = make_scheme(min_age=18, max_age=45, farmer_required=1, income_limit=300000)
    good = {"age": 30, "farmer": "Yes", "annual_family_income": 100000}
    bad = {"age": 30, "farmer": "No", "annual_family_income": 100000}
    assert evaluate_eligibility(good, scheme).is_eligible is True
    assert evaluate_eligibility(bad, scheme).is_eligible is False
