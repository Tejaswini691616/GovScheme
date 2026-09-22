# PATH: GovScheme/models/system_settings_model.py
"""
Runtime, admin-configurable settings that must survive app restarts but
shouldn't require editing .env and redeploying (master prompt: admin-chosen
scheme-refresh interval, discovery mode). Stored in the `system_settings`
table rather than the `.env` file, since these are operational toggles an
admin flips from the UI, not deployment secrets.
"""
from models.db import query_one, execute

DEFAULTS = {
    "scheme_discovery_source": "none",     # "none" | "mock_demo" | "official_api" | "india_gov"
    "scheme_check_interval_hours": "24",   # admin-selectable: 2/3/6/12/24
}


def get_setting(key: str) -> str:
    row = query_one("SELECT setting_value FROM system_settings WHERE setting_key = ?", (key,))
    if row:
        return row["setting_value"]
    return DEFAULTS.get(key)


def set_setting(key: str, value: str):
    execute("""
        INSERT INTO system_settings (setting_key, setting_value, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value,
                                                updated_at = datetime('now')
    """, (key, str(value)))


def get_discovery_source() -> str:
    return get_setting("scheme_discovery_source") or "none"


def get_check_interval_hours() -> int:
    try:
        return int(get_setting("scheme_check_interval_hours"))
    except (TypeError, ValueError):
        return 24
