# PATH: GovScheme/tests/test_digilocker.py
import json
import sqlite3

from database.build_db import _create_missing_tables
from models import db as db_module
from services import document_readiness
from services import digilocker_service


def _setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(db_module.Config, "DATABASE_PATH", str(db_path))
    conn = sqlite3.connect(db_path)
    _create_missing_tables(conn)
    conn.execute("INSERT INTO users(full_name,email,password_hash) VALUES(?,?,?)", ("Test User", "test@example.com", "hash"))
    conn.execute("INSERT INTO schemes(scheme_id,scheme_name,verification_status,source_url) VALUES(?,?,?,?)", ("S1", "Test Scheme", "VERIFIED_SOURCE", "https://example.gov.in/s1"))
    conn.execute("INSERT INTO scheme_document_requirements(scheme_id,document_type,description,source_url,source_name,verification_status) VALUES(?,?,?,?,?,?)",
                 ("S1", "Identity Certificate", "Identity proof", "https://example.gov.in/s1", "Example Govt", "VERIFIED_SOURCE"))
    conn.commit(); conn.close()
    return 1


def test_readiness_does_not_infer_from_profile(monkeypatch, tmp_path):
    user_id = _setup_db(monkeypatch, tmp_path)
    user = {"user_id": user_id, "full_name": "Test User", "phone": "9999999999", "annual_income": 1000, "caste": "General", "farmer": "Yes"}
    result = document_readiness.get_readiness(user, "S1")
    assert result["percentage"] == 0
    assert result["items"][0]["status"] == "VERIFICATION_REQUIRED"


def test_readiness_uses_authorized_metadata_only(monkeypatch, tmp_path):
    user_id = _setup_db(monkeypatch, tmp_path)
    user = {"user_id": user_id}
    digilocker_service.save_connection_state(user_id, "CONNECTED")
    db_module.execute("INSERT INTO document_records(user_id,document_type,source,availability_status,metadata_json) VALUES(?,?,?,?,?)",
                      (user_id, "Identity Certificate", "DigiLocker", "AVAILABLE", json.dumps({"document_type": "Identity Certificate"})))
    result = document_readiness.get_readiness(user, "S1")
    assert result["percentage"] == 100
    assert result["items"][0]["status"] == "AVAILABLE"


def test_integration_configuration_requires_all_operator_values(monkeypatch):
    for attr in ("DIGILOCKER_ENABLED", "DIGILOCKER_CLIENT_ID", "DIGILOCKER_AUTH_URL", "DIGILOCKER_TOKEN_URL", "DIGILOCKER_DOCUMENTS_URL", "DIGILOCKER_REDIRECT_URI"):
        monkeypatch.setattr(digilocker_service.Config, attr, False if attr == "DIGILOCKER_ENABLED" else "")
    assert digilocker_service.integration_configured() is False


def test_document_requirement_matching_is_source_grounded(monkeypatch, tmp_path):
    user_id = _setup_db(monkeypatch, tmp_path)
    user = {"user_id": user_id, "full_name": "Test User", "phone": "9999999999", "annual_income": 1000}
    result = document_readiness.get_readiness(user, "S1")
    assert result["items"][0]["required_by_scheme"] == "Example Govt"
    assert result["items"][0]["source_url"] == "https://example.gov.in/s1"
