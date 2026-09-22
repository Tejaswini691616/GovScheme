# PATH: GovScheme/rpa/application_request.py
"""
RPA application automation (spec sections 55-59).

RPA_MODE=DEMO (default): runs the built-in DEMO government portal
simulator. All generated application numbers are prefixed "DEMO-" and are
NEVER presented as a real government submission (spec section 12/56).

RPA_MODE=UIPATH: calls a UiPath Orchestrator job via REST (requires a real
Orchestrator + a published process; see rpa/uipath/README.md). This code
path will raise a clear error if Orchestrator isn't reachable rather than
silently falling back to fake success.

Never automates CAPTCHA/OTP/biometric/login-control bypass (spec 56/47).
"""
import json
import random
import string
import time

import requests

from config import Config
from models.db import execute


class RPAError(Exception):
    pass


def _generate_demo_reference(scheme_id: str) -> str:
    suffix = "".join(random.choices(string.digits, k=8))
    return f"DEMO-{scheme_id}-{suffix}"


def submit_application(application_id: int, user_row: dict, scheme_row: dict) -> dict:
    """
    Structured input (spec 57): application_id, user info, scheme info.
    Structured output (spec 58): status, application_number, remarks, timestamp.
    """
    rpa_job_id = execute("""
        INSERT INTO rpa_jobs (application_id, status, started_at)
        VALUES (?, 'Running', datetime('now'))
    """, (application_id,))

    try:
        if Config.RPA_MODE.upper() == "UIPATH":
            result = _run_via_uipath_orchestrator(application_id, user_row, scheme_row)
        else:
            result = _run_demo_portal(application_id, user_row, scheme_row)
    except Exception as exc:  # noqa: BLE001 - RPA errors must not crash the app
        result = {
            "status": "Needs Manual Action",
            "application_number": None,
            "remarks": f"RPA automation failed: {exc}",
        }

    execute("""
        UPDATE rpa_jobs SET status = ?, application_number = ?, remarks = ?,
        completed_at = datetime('now') WHERE rpa_job_id = ?
    """, (result["status"], result.get("application_number"), result.get("remarks"), rpa_job_id))

    return result


def _run_demo_portal(application_id, user_row, scheme_row) -> dict:
    """
    Simulates: Open portal -> Navigate -> Enter repetitive info ->
    Upload permitted documents -> Submit -> Read reference number.
    This never touches a real website; it's an in-process simulator so
    the demo works with zero external dependencies.
    """
    time.sleep(0.2)  # simulate navigation
    if not user_row.get("full_name") or not user_row.get("annual_income"):
        return {
            "status": "Needs Manual Action",
            "application_number": None,
            "remarks": "Required profile fields missing for demo submission (name/income).",
        }
    reference = _generate_demo_reference(scheme_row["scheme_id"])
    return {
        "status": "Completed",
        "application_number": reference,
        "remarks": "Simulated submission via Yojana Bharath DEMO government portal. "
                   "This is NOT a real government application. Verify with the "
                   "official source before relying on this reference number.",
    }


def _run_via_uipath_orchestrator(application_id, user_row, scheme_row) -> dict:
    """Start and poll a UiPath Orchestrator job using OAuth client credentials.

    The release key and tenant-specific URL remain deployment configuration;
    no credential or OTP/CAPTCHA automation is performed here.
    """
    base = (Config.UIPATH_ORCHESTRATOR_URL or "").rstrip("/")
    if not base:
        raise RPAError("UIPATH_ORCHESTRATOR_URL is not configured in .env.")
    if not Config.UIPATH_ORCHESTRATOR_CLIENT_ID or not Config.UIPATH_ORCHESTRATOR_CLIENT_SECRET:
        raise RPAError("UiPath client credentials are not configured in .env.")
    if not Config.UIPATH_RELEASE_KEY:
        raise RPAError("UIPATH_RELEASE_KEY is not configured in .env.")

    # UiPath installations expose the identity token endpoint below the
    # Orchestrator host. If your tenant uses a different identity host, put
    # that host in UIPATH_ORCHESTRATOR_URL.
    token_url = f"{base}/identity_/connect/token"
    token_resp = requests.post(
        token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": Config.UIPATH_ORCHESTRATOR_CLIENT_ID,
            "client_secret": Config.UIPATH_ORCHESTRATOR_CLIENT_SECRET,
            "scope": "OR.Jobs OR.Execution",
        },
        timeout=20,
    )
    if not token_resp.ok:
        raise RPAError(f"UiPath authentication failed (HTTP {token_resp.status_code}).")
    token = token_resp.json().get("access_token")
    if not token:
        raise RPAError("UiPath authentication response did not contain an access token.")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
               "X-UIPATH-TenantName": Config.UIPATH_ORCHESTRATOR_TENANT}
    portal_url = scheme_row.get("application_link") or scheme_row.get("official_link")
    if not portal_url:
        raise RPAError("No official application portal is configured for this scheme.")

    arguments = {
        "in_ApplicationId": application_id,
        "in_CitizenFullName": user_row.get("full_name"),
        "in_CitizenAnnualIncome": user_row.get("annual_income"),
        "in_SchemeId": scheme_row.get("scheme_id"),
        "in_SchemeName": scheme_row.get("scheme_name"),
        "in_PortalUrl": portal_url,
    }
    start_url = f"{base}/odata/Jobs/UiPath.Server.Configuration.OData.StartJobs"
    response = requests.post(
        start_url, headers=headers,
        json={"startInfo": {"ReleaseKey": Config.UIPATH_RELEASE_KEY,
                             "Strategy": "ModernJobsCount", "JobsCount": 1,
                             "InputArguments": json.dumps(arguments)}},
        timeout=30,
    )
    if not response.ok:
        raise RPAError(f"UiPath job start failed (HTTP {response.status_code}).")

    payload = response.json() if response.content else {}
    job_id = payload.get("value", [{}])[0].get("Id") if isinstance(payload.get("value"), list) else payload.get("Id")
    if not job_id:
        raise RPAError("UiPath did not return a job id.")

    deadline = time.time() + 120
    terminal = {"Successful", "Faulted", "Stopped", "Unknown"}
    last_state = "Pending"
    while time.time() < deadline:
        poll = requests.get(f"{base}/odata/Jobs({job_id})", headers=headers, timeout=20)
        if not poll.ok:
            raise RPAError(f"UiPath job status request failed (HTTP {poll.status_code}).")
        job = poll.json()
        last_state = job.get("State") or last_state
        if last_state in terminal:
            if last_state != "Successful":
                return {"status":"Needs Manual Action", "application_number":None,
                        "remarks":f"UiPath job {job_id} ended with state {last_state}."}
            outputs = job.get("OutputArguments") or job.get("Output") or {}
            if isinstance(outputs, str):
                try: outputs = json.loads(outputs)
                except json.JSONDecodeError: outputs = {}
            return {
                "status": outputs.get("out_Status") or "Submitted",
                "application_number": outputs.get("out_ApplicationNumber"),
                "remarks": outputs.get("out_Remarks") or f"UiPath job {job_id} completed successfully.",
            }
        time.sleep(3)

    return {"status":"Needs Manual Action", "application_number":None,
            "remarks":f"UiPath job {job_id} did not reach a terminal state before the timeout (last state: {last_state})."}
