# PATH: GovScheme/services/document_readiness.py
"""Scheme-specific document readiness grounded in verified source records.

A profile field is never treated as proof that a document exists. Document
availability comes only from an authorized document provider (currently the
DigiLocker integration boundary) or an explicitly verified record.
"""
from datetime import datetime, timezone

from models.db import query, execute
from services.digilocker_service import get_connection, integration_configured


def _normalise(value):
    return " ".join(str(value or "").strip().lower().split())


def get_verified_requirements(scheme_id):
    return query(
        """SELECT requirement_id,scheme_id,document_type,description,source_url,source_name,
                  verification_status,source_checked_at
           FROM scheme_document_requirements
           WHERE scheme_id=? AND verification_status IN ('VERIFIED_SOURCE','Verified (admin reviewed)')
           ORDER BY document_type""",
        (scheme_id,),
    )


def _document_records(user_id):
    return query("SELECT * FROM document_records WHERE user_id=?", (user_id,))


def get_readiness(user, scheme_id=None):
    """Return readiness only when verified scheme requirements exist.

    If requirements have not been verified from an official source, the
    service reports VERIFICATION_REQUIRED rather than guessing from profile
    fields. This is intentionally conservative.
    """
    if not scheme_id:
        return {
            "status": "VERIFICATION_REQUIRED",
            "percentage": None,
            "items": [],
            "message": "Select a scheme with verified document requirements to calculate readiness.",
        }

    requirements = get_verified_requirements(scheme_id)
    if not requirements:
        return {
            "status": "VERIFICATION_REQUIRED",
            "percentage": None,
            "items": [],
            "message": "Document requirements for this scheme have not yet been verified from an official source, so readiness cannot be calculated.",
        }

    records = _document_records(user["user_id"])
    by_name = {_normalise(r["document_type"]): r for r in records}
    items = []
    for req in requirements:
        record = by_name.get(_normalise(req["document_type"]))
        if record:
            raw = str(record.get("availability_status") or "UNKNOWN").upper()
            if raw in {"AVAILABLE", "VERIFIED"}:
                status = raw
            elif raw == "MISSING":
                status = "MISSING"
            else:
                status = "VERIFICATION_REQUIRED"
            source = record.get("source") or "DigiLocker"
            last_checked = record.get("updated_at") or record.get("verified_at")
        else:
            status = "MISSING" if connection_state(user["user_id"]) == "CONNECTED" else "VERIFICATION_REQUIRED"
            source = "DigiLocker"
            last_checked = None
        items.append({
            "document_type": req["document_type"],
            "description": req.get("description"),
            "status": status,
            "source": source,
            "required_by_scheme": req["source_name"] or req["source_url"],
            "source_url": req["source_url"],
            "last_checked": last_checked,
        })

    ready = sum(i["status"] in {"AVAILABLE", "VERIFIED"} for i in items)
    percentage = round(ready / len(items) * 100)
    return {
        "status": "READY" if ready == len(items) else "PARTIAL" if ready else "MISSING",
        "percentage": percentage,
        "items": items,
        "message": "Readiness is based only on verified scheme requirements and authorized document metadata.",
    }


def record_verified_scheme_requirements(scheme_id, source_url, source_name, documents):
    """Replace the requirements for a scheme with source-verified records.

    `documents` must originate from a reviewed official source. Empty input
    removes no existing verified requirements; this prevents an incomplete
    scrape from silently erasing trusted information.
    """
    cleaned = []
    for item in documents or []:
        if isinstance(item, str):
            document_type, description = item.strip(), None
        else:
            document_type = str(item.get("document_type") or item.get("name") or "").strip()
            description = item.get("description")
        if document_type:
            cleaned.append((document_type, description))
    if not cleaned:
        return 0
    for document_type, description in cleaned:
        execute(
            """INSERT INTO scheme_document_requirements
               (scheme_id,document_type,description,source_url,source_name,verification_status)
               VALUES(?,?,?,?,?,'VERIFIED_SOURCE')
               ON CONFLICT(scheme_id,document_type) DO UPDATE SET
                 description=excluded.description,source_url=excluded.source_url,
                 source_name=excluded.source_name,verification_status='VERIFIED_SOURCE',
                 source_checked_at=datetime('now')""",
            (scheme_id, document_type, description, source_url, source_name),
        )
    return len(cleaned)


def connection_state(user_id):
    row = get_connection(user_id)
    if not row:
        return "NOT_CONNECTED"
    status = row.get("status") or "NOT_CONNECTED"
    if status == "CONNECTED":
        expires_at = row.get("expires_at")
        if expires_at:
            try:
                expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if expiry <= datetime.now(timezone.utc):
                    return "EXPIRED"
            except ValueError:
                return "VERIFICATION_REQUIRED"
        if not integration_configured():
            return "UNAVAILABLE"
    return status


def integration_status():
    return {
        "enabled": bool(integration_configured()),
        "configured": bool(integration_configured()),
        "official_portal": "https://www.digilocker.gov.in/",
    }
