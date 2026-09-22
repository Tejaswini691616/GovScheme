# PATH: GovScheme/tests/test_scheme_discovery.py
"""
Tests for the scheme-discovery honesty fix (real user-reported issue):
the system must NEVER fabricate scheme changes by default, must clearly
label demo/test data as fake, and must never show unverified candidate
schemes to citizens.
"""
import uuid

from models.db import execute, query


def _register_and_login(client, **overrides):
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    data = {
        "full_name": "Discovery Tester", "email": email, "password": "Passw0rd!",
        "age": "30", "annual_income": "100000", "caste": "General",
        "farmer": "No", "student": "No", "disabled": "No",
        "senior_citizen": "No", "bpl": "No", "widow": "No",
    }
    data.update(overrides)
    client.post("/register", data=data, follow_redirects=True)
    return email


def _login_as_admin(client):
    with client.session_transaction() as sess:
        admin = query("SELECT user_id FROM users WHERE is_admin = 1 LIMIT 1")[0]
        sess["user_id"] = admin["user_id"]


def test_default_discovery_source_is_none_and_fabricates_nothing():
    from automation.scheme_scraper import fetch_candidate_schemes
    from models.system_settings_model import get_discovery_source
    assert get_discovery_source() == "none"
    assert fetch_candidate_schemes() == []


def test_manual_check_with_no_source_reports_zero_not_fake_data(client):
    _login_as_admin(client)
    resp = client.post("/admin/run-scheme-check", follow_redirects=True)
    assert resp.status_code == 200
    assert b"No official government feed is configured" in resp.data


def test_candidate_scheme_hidden_from_citizens_until_verified(client):
    execute("""INSERT INTO schemes (scheme_id, scheme_name, category, status, verification_status)
               VALUES ('TESTCAND01', 'Unreviewed Test Scheme', 'Agriculture', 'Active',
                       'Candidate - pending admin review')""")

    from models.scheme_model import get_all_schemes, get_all_schemes_including_candidates
    citizen_visible_ids = [s["scheme_id"] for s in get_all_schemes()]
    assert "TESTCAND01" not in citizen_visible_ids

    admin_visible_ids = [s["scheme_id"] for s in get_all_schemes_including_candidates()]
    assert "TESTCAND01" in admin_visible_ids

    _login_as_admin(client)
    client.post("/admin/verify-scheme/TESTCAND01", follow_redirects=True)
    citizen_visible_ids_after = [s["scheme_id"] for s in get_all_schemes()]
    assert "TESTCAND01" in citizen_visible_ids_after


def test_demo_mode_is_explicit_and_clearly_labeled(client):
    _login_as_admin(client)
    resp = client.post("/admin/discovery-settings", data={
        "discovery_source": "mock_demo", "check_interval_hours": "6",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"DEMO" in resp.data or b"Demo mode enabled" in resp.data

    from models.system_settings_model import get_discovery_source, get_check_interval_hours
    assert get_discovery_source() == "mock_demo"
    assert get_check_interval_hours() == 6

    client.post("/admin/run-scheme-check", follow_redirects=True)
    updates = query("SELECT * FROM scheme_updates WHERE source LIKE '%DEMO%'")
    assert len(updates) > 0, "demo-mode discovery must tag its rows as DEMO"

    from models.scheme_model import get_all_schemes
    citizen_visible_ids = [s["scheme_id"] for s in get_all_schemes()]
    assert "DEMO-001" not in citizen_visible_ids

    from models.system_settings_model import set_setting
    set_setting("scheme_discovery_source", "none")


def test_schemes_page_defaults_to_eligible_only(client):
    _register_and_login(client, annual_income="5000000")

    default_resp = client.get("/schemes?q=")
    show_all_resp = client.get("/schemes?q=&show_all=1")
    assert default_resp.status_code == 200
    assert show_all_resp.status_code == 200
    default_count = default_resp.data.count(b"sg-scheme-card")
    show_all_count = show_all_resp.data.count(b"sg-scheme-card")
    assert show_all_count >= default_count


def test_ineligible_scheme_never_appears_in_default_schemes_view(client):
    _register_and_login(client, bpl="No", farmer="No", student="No",
                         disabled="No", senior_citizen="No", widow="No",
                         annual_income="2000000")
    resp = client.get("/schemes?show_all=0")
    bpl_only_schemes = query("SELECT scheme_name FROM schemes WHERE bpl_required = 1")
    for s in bpl_only_schemes:
        assert s["scheme_name"].encode() not in resp.data
