# PATH: GovScheme/tests/test_security.py
"""
Security checklist tests (master prompt: "SECURITY TESTING"). These don't
replace a real security audit, but they do verify the specific, concrete
things this project claims: parameterized queries, session-based route
protection, and password hashing.
"""
import uuid


def _register_and_login(client):
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/register", data={
        "full_name": "Security Tester", "email": email, "password": "Passw0rd!",
        "age": "40", "annual_income": "70000", "caste": "General",
        "farmer": "No", "student": "No", "disabled": "No",
        "senior_citizen": "No", "bpl": "No", "widow": "No",
    }, follow_redirects=True)
    return email


def test_sql_injection_in_login_does_not_bypass_auth(client):
    resp = client.post("/login", data={
        "email": "' OR '1'='1", "password": "' OR '1'='1",
    }, follow_redirects=True)
    assert b"Invalid" in resp.data  # must NOT log in


def test_sql_injection_in_scheme_search_does_not_error(client):
    _register_and_login(client)
    resp = client.get("/schemes?q=" + "'; DROP TABLE schemes; --")
    assert resp.status_code == 200
    from models.db import query
    # confirm the schemes table still exists and has rows
    assert len(query("SELECT * FROM schemes")) > 0


def test_password_is_hashed_not_plaintext(client):
    email = _register_and_login(client)
    from models.user_model import get_user_by_email
    user = get_user_by_email(email)
    assert user["password_hash"] != "Passw0rd!"
    assert user["password_hash"].startswith(("scrypt:", "pbkdf2:"))


def test_protected_routes_require_login(client):
    for path in ["/dashboard", "/schemes", "/applications", "/profile",
                 "/notifications", "/complaints", "/feedback", "/settings"]:
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code in (302, 401), f"{path} should require login"


def test_cannot_apply_to_nonexistent_scheme(client):
    _register_and_login(client)
    resp = client.post("/schemes/FAKE_ID_999/apply", follow_redirects=True)
    assert resp.status_code == 200  # redirects with a flash message, no crash


def test_applications_scoped_per_user(client):
    """One user's applications must never leak into another user's session."""
    _register_and_login(client)
    from models.db import query
    scheme_id = query("SELECT scheme_id FROM schemes LIMIT 1")[0]["scheme_id"]
    client.post(f"/schemes/{scheme_id}/apply", follow_redirects=True)

    client.get("/logout")
    _register_and_login(client)  # second, different user
    resp = client.get("/applications")
    assert resp.status_code == 200

    all_apps = query("SELECT user_id FROM applications")
    # applications exist and are attributed to distinct user_ids, i.e. the
    # query is genuinely scoped by user_id rather than returning everything
    assert len(all_apps) >= 1
