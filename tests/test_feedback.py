# PATH: GovScheme/tests/test_feedback.py
import uuid


def _register_and_login(client):
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/register", data={
        "full_name": "Feedback Tester", "email": email, "password": "Passw0rd!",
        "age": "28", "annual_income": "60000", "caste": "General",
        "farmer": "No", "student": "No", "disabled": "No",
        "senior_citizen": "No", "bpl": "No", "widow": "No",
    }, follow_redirects=True)
    return email


def test_feedback_page_loads(client):
    _register_and_login(client)
    resp = client.get("/feedback")
    assert resp.status_code == 200


def test_submit_valid_feedback(client):
    _register_and_login(client)
    resp = client.post("/feedback", data={
        "rating": "5", "comment": "Very helpful chatbot!", "feature": "Chatbot",
    }, follow_redirects=True)
    assert resp.status_code == 200

    from models.feedback_model import get_feedback_summary
    summary = get_feedback_summary()
    assert summary["total_feedback"] >= 1


def test_submit_invalid_rating_rejected(client):
    _register_and_login(client)
    resp = client.post("/feedback", data={"rating": "9", "comment": "bad rating"}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"between 1 and 5" in resp.data


def test_feedback_summary_star_breakdown(client):
    _register_and_login(client)
    from models.feedback_model import create_feedback, get_feedback_summary
    create_feedback(1, 5, "Great", feature="Website")
    create_feedback(1, 1, "Bad", feature="Website")
    summary = get_feedback_summary()
    assert summary["star_counts"][5] >= 1
    assert summary["star_counts"][1] >= 1
