# PATH: GovScheme/tests/test_eligibility_simulator.py
import uuid


def _register_and_login(client, **overrides):
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    data = {
        "full_name": "Sim Tester", "email": email, "password": "Passw0rd!",
        "age": "30", "annual_income": "800000", "caste": "General",
        "farmer": "No", "student": "No", "disabled": "No",
        "senior_citizen": "No", "bpl": "No", "widow": "No",
    }
    data.update(overrides)
    client.post("/register", data=data, follow_redirects=True)
    return email


def test_simulator_never_modifies_real_profile(client):
    email = _register_and_login(client)
    resp = client.post("/api/eligibility-simulator", json={"farmer": "Yes", "annual_income": 50000})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "before" in data and "after" in data and "delta" in data

    from models.user_model import get_user_by_email
    user = get_user_by_email(email)
    # The real saved profile must be untouched by the simulation.
    assert user["farmer"] == "No"
    assert user["annual_income"] == 800000


def test_simulator_lower_income_increases_or_maintains_eligibility(client):
    """Lowering income should never make a citizen eligible for FEWER
    income-capped schemes than before - it should only add or keep the same."""
    _register_and_login(client)
    resp = client.post("/api/eligibility-simulator", json={"annual_income": 50000})
    data = resp.get_json()
    assert data["after"] >= data["before"]


def test_simulator_rejects_invalid_income(client):
    _register_and_login(client)
    resp = client.post("/api/eligibility-simulator", json={"annual_income": "not-a-number"})
    assert resp.status_code == 400
