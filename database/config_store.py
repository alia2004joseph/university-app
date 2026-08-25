"""database/config_store.py — Generic key/value app settings (replaces
the 'Config' sheet used by the Super Admin console)."""

from typing import Dict, Optional

from .supabase_client import get_client, safe_call


def get_all_config() -> Dict:
    def _run():
        res = get_client().table("app_config").select("*").execute()
        return {row["key"]: row["value"] for row in (res.data or [])}
    return safe_call(_run, default={}, log_label="get_all_config")


def get_config_value(key: str) -> Optional[str]:
    def _run():
        res = get_client().table("app_config").select("value").eq("key", key).limit(1).execute()
        return res.data[0]["value"] if res.data else None
    return safe_call(_run, default=None, log_label="get_config_value")


def set_config(key: str, value: str, description: str = "") -> Dict:
    def _run():
        get_client().table("app_config").upsert({
            "key": key.strip(), "value": value.strip(), "description": description.strip(),
        }, on_conflict="key").execute()
        return {"status": "success"}
    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="set_config")
