# PATH: GovScheme/config.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass


def _env(name, default=""):
    return os.getenv(name, default).strip()


def _bool(name, default=False):
    return _env(name, "1" if default else "0") == "1"


class Config:
    SECRET_KEY = _env("FLASK_SECRET_KEY", "dev-only-change-me")
    DEBUG = _bool("FLASK_DEBUG", True)
    TESTING = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)
    MAX_CONTENT_LENGTH = int(_env("MAX_UPLOAD_MB", "10")) * 1024 * 1024

    DATABASE_PATH = str(BASE_DIR / _env("DATABASE_PATH", "database/YojanaBharath.db"))
    EXCEL_SOURCE_PATH = str(BASE_DIR / _env("EXCEL_SOURCE_PATH", "data/Government_Scheme_Eligibility_Upgraded.xlsx"))

    ML_MODEL_PATH = str(BASE_DIR / _env("ML_MODEL_PATH", "ml_models/trained_model.joblib"))
    ML_METRICS_PATH = str(BASE_DIR / "ml_models" / "metrics.json")

    LLM_API_KEY = _env("LLM_API_KEY")
    LLM_PROVIDER = _env("LLM_PROVIDER")

    STT_PROVIDER = _env("STT_PROVIDER", "browser_web_speech")
    STT_API_KEY = _env("STT_API_KEY")
    STT_REGION = _env("STT_REGION")

    TTS_PROVIDER = _env("TTS_PROVIDER", "browser_web_speech")
    TTS_API_KEY = _env("TTS_API_KEY")
    TTS_REGION = _env("TTS_REGION")

    SCHEME_UPDATE_INTERVAL_HOURS = int(_env("SCHEME_UPDATE_INTERVAL_HOURS", "24"))
    OFFICIAL_SCHEME_FEED_URL = _env("OFFICIAL_SCHEME_FEED_URL")
    OFFICIAL_SCHEME_FEED_IS_COMPLETE = _bool("OFFICIAL_SCHEME_FEED_IS_COMPLETE", False)

    MAIL_SERVER = _env("MAIL_SERVER")
    MAIL_PORT = int(_env("MAIL_PORT", "587"))
    MAIL_USERNAME = _env("MAIL_USERNAME", _env("EMAIL_ADDRESS"))
    MAIL_PASSWORD = _env("MAIL_PASSWORD", _env("EMAIL_PASSWORD"))
    MAIL_USE_TLS = _bool("MAIL_USE_TLS", True)
    MAIL_FROM = _env("MAIL_FROM", MAIL_USERNAME)

    RPA_MODE = _env("RPA_MODE", "DEMO").upper()
    UIPATH_ORCHESTRATOR_URL = _env("UIPATH_ORCHESTRATOR_URL")
    UIPATH_ORCHESTRATOR_TENANT = _env("UIPATH_ORCHESTRATOR_TENANT")
    UIPATH_ORCHESTRATOR_CLIENT_ID = _env("UIPATH_ORCHESTRATOR_CLIENT_ID")
    UIPATH_ORCHESTRATOR_CLIENT_SECRET = _env("UIPATH_ORCHESTRATOR_CLIENT_SECRET")
    UIPATH_RELEASE_KEY = _env("UIPATH_RELEASE_KEY")

    DIGILOCKER_ENABLED = _bool("DIGILOCKER_ENABLED", False)
    DIGILOCKER_AUTH_URL = _env("DIGILOCKER_AUTH_URL", "https://www.digilocker.gov.in/")
    # These are operator-supplied values from an authorized DigiLocker
    # integration. SmartGov AI never guesses or scrapes DigiLocker endpoints.
    DIGILOCKER_CLIENT_ID = _env("DIGILOCKER_CLIENT_ID")
    DIGILOCKER_CLIENT_SECRET = _env("DIGILOCKER_CLIENT_SECRET")
    DIGILOCKER_TOKEN_URL = _env("DIGILOCKER_TOKEN_URL")
    DIGILOCKER_DOCUMENTS_URL = _env("DIGILOCKER_DOCUMENTS_URL")
    DIGILOCKER_REDIRECT_URI = _env("DIGILOCKER_REDIRECT_URI")
    DIGILOCKER_SCOPE = _env("DIGILOCKER_SCOPE", "openid")

    ADMIN_EMAILS = [
        value.lower() for value in (
            _env("ADMIN_EMAIL_1", "tejaswinip1123@gmail.com"),
            _env("ADMIN_EMAIL_2"), _env("ADMIN_EMAIL_3"), _env("ADMIN_EMAIL_4"),
        ) if value
    ]

    DISCLAIMER = (
        "SmartGov AI provides prototype eligibility and recommendation assistance based on "
        "available scheme data and configured criteria. Final eligibility, benefits, documents "
        "and application requirements must be verified using the official government source "
        "before applying."
    )
