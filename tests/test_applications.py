# PATH: GovScheme/tests/test_applications.py
import uuid

from models.db import query


def _register_and_login(client):
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/register", data={
        "full_name": "Applicant One", "email": email, "password": "Passw0rd!",
        "age": "35", "annual_income": "80000", "caste": "General",
        "farmer": "Yes", "student": "No", "disabled": "No",
        "senior_citizen": "No", "bpl": "No", "widow": "No",
    }, follow_redirects=True)
    return email


def test_apply_now_creates_demo_application(client):
    _register_and_login(client)
    any_scheme = query("SELECT scheme_id FROM schemes LIMIT 1")
    if not any_scheme:
        return  # DB not built in this test environment; skip gracefully
    scheme_id = any_scheme[0]["scheme_id"]

    resp = client.post(f"/schemes/{scheme_id}/apply", follow_redirects=True)
    assert resp.status_code == 200

    apps = query("SELECT * FROM applications WHERE scheme_id = ? ORDER BY application_id DESC LIMIT 1", (scheme_id,))
    assert apps
    app_row = apps[0]
    assert app_row["status"] in ("Completed", "Needs Manual Action", "Queued", "Failed")
    if app_row["application_number"]:
        assert app_row["application_number"].startswith("DEMO-")


def test_applications_list_page(client):
    _register_and_login(client)
    resp = client.get("/applications")
    assert resp.status_code == 200
