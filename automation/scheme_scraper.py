# PATH: GovScheme/automation/scheme_scraper.py
"""Scheme collection from an explicitly configured official JSON feed.

No feed is silently guessed. The admin must configure OFFICIAL_SCHEME_FEED_URL
and review candidates before they become trusted catalogue entries.
"""
import json
import os
import requests
from urllib.parse import urlparse, urljoin
from html.parser import HTMLParser
import hashlib
from config import Config

MOCK_FEED_PATH = os.path.join(os.path.dirname(__file__), "mock_official_feed.json")


class SchemeDiscoveryError(Exception):
    pass


def fetch_candidate_schemes() -> list:
    from models.system_settings_model import get_discovery_source
    source = get_discovery_source()
    if source == "none":
        return []
    if source == "mock_demo":
        if not os.path.exists(MOCK_FEED_PATH):
            return []
        with open(MOCK_FEED_PATH, encoding="utf-8") as f:
            rows = json.load(f)
        for row in rows:
            row["_demo_data"] = True
        return rows
    if source == "official_api":
        return _fetch_from_official_api()
    if source == "india_gov":
        return _fetch_from_india_gov()
    return []


def _fetch_from_official_api() -> list:
    url = Config.OFFICIAL_SCHEME_FEED_URL
    if not url:
        raise SchemeDiscoveryError("OFFICIAL_SCHEME_FEED_URL is not configured.")
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not (hostname.endswith(".gov.in") or hostname.endswith(".nic.in")):
        raise SchemeDiscoveryError("Official scheme feed must use an HTTPS .gov.in or .nic.in host.")
    try:
        response = requests.get(url, timeout=20, headers={"User-Agent": "SmartGovAI/1.0"})
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise SchemeDiscoveryError(f"Official scheme feed could not be read: {exc}") from exc
    rows = payload.get("schemes", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise SchemeDiscoveryError("Official feed must return a JSON list or {\"schemes\": [...] }.")
    required = {"scheme_id", "scheme_name"}
    cleaned = []
    for row in rows:
        if not isinstance(row, dict) or not required.issubset(row):
            continue
        row = dict(row)
        row["_official_data"] = True
        row["source_url"] = url
        cleaned.append(row)
    return cleaned


class _IndiaGovLinkParser(HTMLParser):
    """Conservative discovery parser: collect only explicit scheme links.

    It does not infer eligibility, benefits, documents, or application data.
    Every discovered record remains PENDING_REVIEW until an admin verifies it.
    """
    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.current_href = None
        self.current_text = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.current_href = urljoin(self.base_url, href)
            self.current_text = []

    def handle_data(self, data):
        if self.current_href:
            self.current_text.append(data.strip())

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.current_href:
            text = " ".join(x for x in self.current_text if x).strip()
            href = self.current_href
            parsed = urlparse(href)
            host = (parsed.hostname or "").lower().rstrip(".")
            if host in {"www.india.gov.in", "india.gov.in"} and text and "/my-government/schemes" in parsed.path and href.rstrip("/") != self.base_url.rstrip("/"):
                self.links.append((text, href))
            self.current_href = None
            self.current_text = []


def _fetch_from_india_gov() -> list:
    source_url = "https://www.india.gov.in/my-government/schemes"
    try:
        response = requests.get(source_url, timeout=20, headers={"User-Agent": "SmartGovAI/1.0"})
        response.raise_for_status()
    except Exception as exc:
        raise SchemeDiscoveryError(f"India.gov.in scheme catalogue could not be read: {exc}") from exc
    parser = _IndiaGovLinkParser(source_url)
    parser.feed(response.text)
    unique = {}
    for name, href in parser.links:
        sid = "INDIA-GOV-" + hashlib.sha256(href.encode("utf-8")).hexdigest()[:16]
        unique[href] = {
            "scheme_id": sid,
            "scheme_name": name,
            "official_link": href,
            "application_link": href,
            "source_url": href,
            "source_name": "India.gov.in",
            "_official_data": True,
        }
    return list(unique.values())
