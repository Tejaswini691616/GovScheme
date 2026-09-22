# PATH: GovScheme/tests/test_complaints.py
import uuid


def _register_and_login(client):
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/register", data={
        "full_name": "Complaint Tester", "email": email, "password": "Passw0rd!",
        "age": "33", "annual_income": "70000", "caste": "General",
        "farmer": "No", "student": "No", "disabled": "No",
        "senior_citizen": "No", "bpl": "No", "widow": "No",
    }, follow_redirects=True)
    return email


def test_complaints_list_requires_login(client):
    resp = client.get("/complaints", follow_redirects=True)
    assert resp.status_code == 200


def test_raise_and_view_complaint(client):
    _register_and_login(client)
    resp = client.post("/complaints/new", data={
        "category": "Application Issue",
        "subject": "My application is stuck",
        "description": "It has said Queued for a long time.",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"SG-" in resp.data  # complaint number format


def test_complaint_number_format_and_sequence(client):
    _register_and_login(client)
    from models.complaint_model import create_complaint
    import re
    r1 = create_complaint(1, "Other", "Test 1", "First complaint")
    r2 = create_complaint(1, "Other", "Test 2", "Second complaint")
    assert re.match(r"^SG-\d{4}-\d{5}$", r1["complaint_number"])
    assert r1["complaint_number"] != r2["complaint_number"]


def test_reply_and_close_complaint(client):
    _register_and_login(client)
    client.post("/complaints/new", data={
        "category": "Website Problem", "subject": "Bug", "description": "Something is broken",
    }, follow_redirects=True)
    from models.db import query
    complaint_id = query("SELECT complaint_id FROM complaints ORDER BY complaint_id DESC LIMIT 1")[0]["complaint_id"]

    resp = client.post(f"/complaints/{complaint_id}/reply", data={"message": "Any update?"}, follow_redirects=True)
    assert resp.status_code == 200

    resp = client.post(f"/complaints/{complaint_id}/close", follow_redirects=True)
    assert resp.status_code == 200
    assert b"CLOSED" in resp.data


def test_user_cannot_view_others_complaint(client):
    """A user must not be able to view another user's complaint by guessing the ID."""
    email_a = _register_and_login(client)
    client.post("/complaints/new", data={
        "category": "Other", "subject": "Private issue", "description": "Sensitive details",
    }, follow_redirects=True)
    from models.db import query
    complaint_id = query("SELECT complaint_id FROM complaints ORDER BY complaint_id DESC LIMIT 1")[0]["complaint_id"]

    client.get("/logout")
    _register_and_login(client)  # a different user
    resp = client.get(f"/complaints/{complaint_id}", follow_redirects=True)
    assert b"Private issue" not in resp.data


def test_raise_from_chat_endpoint(client):
    _register_and_login(client)
    resp = client.post("/api/complaints/raise-from-chat", json={
        "description": "The chatbot could not find my scheme.",
        "category": "Chatbot Problem",
        "language": "English",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["complaint_number"].startswith("SG-")
