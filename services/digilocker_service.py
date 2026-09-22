# PATH: GovScheme/services/digilocker_service.py
"""Safe DigiLocker integration boundary.

This module deliberately does not guess DigiLocker endpoints.  An operator
must provide the endpoints/client details supplied by an authorized
DigiLocker integration.  Access tokens are kept in the server-side session
only for the active flow and are never written to SQLite or logs.
"""
import hashlib
import json
import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests

from config import Config
from models.db import execute, query_one


def _now():
    return datetime.now(timezone.utc).isoformat()


def integration_configured():
    return bool(
        Config.DIGILOCKER_ENABLED
        and Config.DIGILOCKER_CLIENT_ID
        and Config.DIGILOCKER_AUTH_URL
        and Config.DIGILOCKER_CLIENT_SECRET
        and Config.DIGILOCKER_TOKEN_URL
        and Config.DIGILOCKER_DOCUMENTS_URL
        and Config.DIGILOCKER_REDIRECT_URI
    )


def create_state():
    return secrets.token_urlsafe(32)


def build_authorization_url(state: str):
    if not Config.DIGILOCKER_ENABLED:
        return Config.DIGILOCKER_AUTH_URL
    if not integration_configured():
        return Config.DIGILOCKER_AUTH_URL
    params = {
        "response_type": "code",
        "client_id": Config.DIGILOCKER_CLIENT_ID,
        "redirect_uri": Config.DIGILOCKER_REDIRECT_URI,
        "scope": Config.DIGILOCKER_SCOPE,
        "state": state,
    }
    return Config.DIGILOCKER_AUTH_URL + ("&" if "?" in Config.DIGILOCKER_AUTH_URL else "?") + urlencode(params)


def save_connection_state(user_id, status, subject=None, checked_at=None, expires_at=None):
    subject_hash = hashlib.sha256(subject.encode("utf-8")).hexdigest() if subject else None
    execute(
        """INSERT INTO digilocker_connections(user_id,status,subject_hash,last_checked,expires_at,updated_at)
           VALUES(?,?,?,?,?,datetime('now'))
           ON CONFLICT(user_id) DO UPDATE SET status=excluded.status,
             subject_hash=excluded.subject_hash,last_checked=excluded.last_checked,expires_at=excluded.expires_at,updated_at=datetime('now')""",
        (user_id, status, subject_hash, checked_at or _now(), expires_at),
    )
    execute(
        "INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)",
        (user_id, "DIGILOCKER_CONNECTION_STATUS", f"status={status}"),
    )


def get_connection(user_id):
    return query_one("SELECT * FROM digilocker_connections WHERE user_id=?", (user_id,))


def exchange_code(code):
    if not integration_configured():
        raise RuntimeError("Authorized DigiLocker integration is not configured.")
    response = requests.post(
        Config.DIGILOCKER_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": Config.DIGILOCKER_REDIRECT_URI,
            "client_id": Config.DIGILOCKER_CLIENT_ID,
            "client_secret": Config.DIGILOCKER_CLIENT_SECRET,
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise RuntimeError("The configured DigiLocker token response did not contain an access token.")
    return payload


def fetch_document_metadata(access_token):
    if not integration_configured():
        raise RuntimeError("Authorized DigiLocker integration is not configured.")
    response = requests.get(
        Config.DIGILOCKER_DOCUMENTS_URL,
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        documents = payload.get("documents", [])
    else:
        documents = payload
    if not isinstance(documents, list):
        raise RuntimeError("The configured DigiLocker document response is not a list.")
    return documents


def sync_document_metadata(user_id, documents, expires_at=None):
    """Persist minimum non-sensitive availability metadata only."""
    for item in documents:
        if not isinstance(item, dict):
            continue
        document_type = str(item.get("document_type") or item.get("type") or item.get("name") or "").strip()
        if not document_type:
            continue
        status = str(item.get("status") or "AVAILABLE").upper()
        if status not in {"AVAILABLE", "VERIFIED", "MISSING", "UNKNOWN"}:
            status = "AVAILABLE"
        metadata = {
            "issuer": item.get("issuer"),
            "document_type": document_type,
            "status": status,
        }
        execute(
            """INSERT INTO document_records(user_id,document_type,source,availability_status,verified_at,metadata_json,updated_at)
               VALUES(?,?,?,?,?,?,datetime('now'))
               ON CONFLICT(user_id,document_type) DO UPDATE SET source=excluded.source,
                 availability_status=excluded.availability_status,verified_at=excluded.verified_at,
                 metadata_json=excluded.metadata_json,updated_at=datetime('now')""",
            (user_id, document_type, "DigiLocker", status,
             _now() if status == "VERIFIED" else None, json.dumps(metadata, ensure_ascii=False)),
        )
    save_connection_state(user_id, "CONNECTED", expires_at=expires_at)
    execute("INSERT INTO audit_logs(user_id,action,details) VALUES(?,?,?)",
            (user_id, "DIGILOCKER_DOCUMENT_METADATA_SYNC", f"document_count={len([x for x in documents if isinstance(x, dict)])}"))
