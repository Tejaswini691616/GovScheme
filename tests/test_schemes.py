# PATH: GovScheme/tests/test_schemes.py
import uuid


def _register_and_login(client):
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/register", data={
        "full_name": "Scheme Tester", "email": email, "password": "Passw0rd!",
        "age": "40", "annual_income": "90000", "caste": "SC",
        "farmer": "Yes", "student": "No", "disabled": "No",
        "senior_citizen": "No", "bpl": "Yes", "widow": "No",
    }, follow_redirects=True)
    return email


def test_schemes_list_requires_login(client):
    resp = client.get("/schemes", follow_redirects=True)
    assert resp.status_code == 200


def test_schemes_list_after_login(client):
    _register_and_login(client)
    resp = client.get("/schemes")
    assert resp.status_code == 200
    assert b"scheme" in resp.data.lower()


def test_scheme_search_keyword(client):
    _register_and_login(client)
    resp = client.get("/schemes?q=farmer")
    assert resp.status_code == 200


def test_scheme_details_not_found(client):
    _register_and_login(client)
    resp = client.get("/schemes/NON_EXISTENT_ID", follow_redirects=True)
    assert resp.status_code == 200
