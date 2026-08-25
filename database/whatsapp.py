"""
database/whatsapp.py — WhatsApp notifications via CallMeBot.

Per the migration brief (section 23): WhatsApp is an OPTIONAL secondary
channel. It reads student phone/API-key data from Supabase now instead
of Google Sheets, but is never a dependency of the core (in-app)
notification system — announcements/materials/etc. work with or
without this succeeding.
"""

import time
from typing import List

import requests

from .supabase_client import get_client, safe_call, none_if_all

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"

# ─────────────────────────────────────────────────────────────
# WHATSAPP DISABLED (by request) — this now always short-circuits
# before making any network call. Every UI element that calls into
# this module (registration, class broadcasts, admin alerts, etc.)
# is unaffected and still runs — it just always behaves as if no
# student has WhatsApp set up. No message can be sent from anywhere
# in the app while this flag is False.
# ─────────────────────────────────────────────────────────────
WHATSAPP_ENABLED = False


def _send_callmebot(phone: str, apikey: str, message: str) -> bool:
    if not WHATSAPP_ENABLED:
        return False
    if not phone or not apikey:
        return False
    try:
        r = requests.get(CALLMEBOT_URL, params={"phone": phone, "text": message, "apikey": apikey}, timeout=15)
        return r.status_code == 200
    except Exception as e:
        print(f"[whatsapp] send error: {e}")
        return False


def notify_student_whatsapp(reg_number: str, message: str) -> bool:
    def _run():
        client = get_client()
        res = client.table("students").select("whatsapp_phone, callmebot_apikey") \
            .eq("reg_number", reg_number.strip().upper()).limit(1).execute()
        if not res.data:
            return False
        row = res.data[0]
        return _send_callmebot(row.get("whatsapp_phone", ""), row.get("callmebot_apikey", ""), message)
    return bool(safe_call(_run, default=False, log_label="notify_student_whatsapp"))


def broadcast_whatsapp(dept: str, year: str, message: str) -> int:
    def _run():
        client = get_client()
        q = client.table("students").select("whatsapp_phone, callmebot_apikey")
        d, y = none_if_all(dept), none_if_all(year)
        if d:
            q = q.eq("department_code", d)
        if y:
            q = q.eq("year", y)
        res = q.execute()
        sent = 0
        for row in (res.data or []):
            if _send_callmebot(row.get("whatsapp_phone", ""), row.get("callmebot_apikey", ""), message):
                sent += 1
            time.sleep(0.4)  # CallMeBot rate limit
        return sent
    return safe_call(_run, default=0, log_label="broadcast_whatsapp")