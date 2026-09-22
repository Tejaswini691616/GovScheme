# PATH: GovScheme/tests/test_settings.py
import uuid


def _register_and_login(client):
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/register", data={
        "full_name": "Settings Tester", "email": email, "password": "Passw0rd!",
        "age": "31", "annual_income": "65000", "caste": "General",
        "farmer": "No", "student": "No", "disabled": "No",
        "senior_citizen": "No", "bpl": "No", "widow": "No",
    }, follow_redirects=True)
    return email


def test_settings_page_loads(client):
    _register_and_login(client)
    resp = client.get("/settings")
    assert resp.status_code == 200


def test_save_dark_theme_persists(client):
    _register_and_login(client)
    resp = client.post("/settings", data={
        "theme_preference": "dark", "text_size": "large", "preferred_language": "Hindi",
    }, follow_redirects=True)
    assert resp.status_code == 200

    # Confirm it persisted to the DB (not just a cookie), so it survives
    # across devices/sessions per the master prompt's requirement.
    from models.db import query
    row = query("SELECT theme_preference, text_size, preferred_language FROM users "
                "WHERE full_name = 'Settings Tester' ORDER BY user_id DESC LIMIT 1")[0]
    assert row["theme_preference"] == "dark"
    assert row["text_size"] == "large"
    assert row["preferred_language"] == "Hindi"


def test_theme_reflected_in_rendered_html(client):
    _register_and_login(client)
    client.post("/settings", data={"theme_preference": "high-contrast", "text_size": "normal"})
    resp = client.get("/dashboard")
    assert b'data-theme="high-contrast"' in resp.data


def test_invalid_theme_falls_back_to_light(client):
    _register_and_login(client)
    resp = client.post("/settings", data={"theme_preference": "not-a-real-theme", "text_size": "normal"},
                        follow_redirects=True)
    assert resp.status_code == 200
    from models.db import query
    row = query("SELECT theme_preference FROM users WHERE full_name = 'Settings Tester' "
                "ORDER BY user_id DESC LIMIT 1")[0]
    assert row["theme_preference"] == "light"
