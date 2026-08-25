"""
database/notifications.py — In-app notification system.

Handles:
  * fan-out: turning one announcement/material into a notification row
    per affected student
  * fetch / unread-count / mark-as-read for the student notification bell
  * a best-effort Supabase Realtime subscription, with a polling fallback
    that Streamlit can safely drive via st.fragment (see notifications_ui.py)

See README_SUPABASE_MIGRATION.md → "Known limitations" for an honest
account of what "realtime" means inside Streamlit's script-rerun model.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .supabase_client import get_client, safe_call, none_if_all

log = logging.getLogger("database.notifications")


# ─────────────────────────────────────────────────────────────
# FAN-OUT: create one notification row per matching student
# ─────────────────────────────────────────────────────────────
def _students_in_scope(dept: str, year: str) -> List[str]:
    client = get_client()
    q = client.table("students").select("reg_number")
    d, y = none_if_all(dept), none_if_all(year)
    if d:
        q = q.eq("department_code", d)
    if y:
        q = q.eq("year", y)
    res = q.execute()
    return [r["reg_number"] for r in (res.data or [])]


def notify_students_for_announcement(announcement_row: Dict, dept: str = "ALL", year: str = "ALL") -> int:
    def _run():
        client = get_client()
        reg_numbers = _students_in_scope(dept, year)
        if not reg_numbers:
            return 0
        title = announcement_row.get("title") or "New Announcement"
        message = announcement_row.get("content", "")[:280]
        rows = [{
            "student_reg": reg,
            "announcement_id": announcement_row.get("id"),
            "title": title,
            "message": message,
            "notification_type": "announcement",
        } for reg in reg_numbers]
        client.table("notifications").insert(rows).execute()

        # Secondary channel: short "check the app" teaser email — never the
        # full announcement text, so students still have to open the app.
        try:
            from .email_notify import notify_students_email_for_announcement
            notify_students_email_for_announcement(announcement_row, dept=dept, year=year)
        except Exception as e:
            log.warning("Email teaser for announcement failed (non-fatal): %s", e)

        return len(rows)
    return safe_call(_run, default=0, log_label="notify_students_for_announcement")


def notify_students_for_material(material_row: Dict, dept: str = "ALL", year: str = "ALL") -> int:
    def _run():
        client = get_client()
        reg_numbers = _students_in_scope(dept, year)
        if not reg_numbers:
            return 0
        rows = [{
            "student_reg": reg,
            "material_id": material_row.get("id"),
            "title": "New Learning Material",
            "message": material_row.get("title", "A new material was uploaded."),
            "notification_type": "material",
        } for reg in reg_numbers]
        client.table("notifications").insert(rows).execute()

        try:
            from .email_notify import notify_students_email_for_material
            notify_students_email_for_material(material_row, dept=dept, year=year)
        except Exception as e:
            log.warning("Email teaser for material failed (non-fatal): %s", e)

        return len(rows)
    return safe_call(_run, default=0, log_label="notify_students_for_material")


def notify_student(reg_number: str, title: str, message: str, notification_type: str = "system") -> bool:
    """Send a single ad-hoc notification, e.g. a feedback reply or a
    timetable change, to one student."""
    def _run():
        get_client().table("notifications").insert({
            "student_reg": reg_number.strip().upper(),
            "title": title,
            "message": message,
            "notification_type": notification_type,
        }).execute()

        try:
            from .email_notify import notify_student_email
            notify_student_email(reg_number, title, message, kind_label="update")
        except Exception as e:
            log.warning("Email teaser for student notification failed (non-fatal): %s", e)

        return True
    return bool(safe_call(_run, default=False, log_label="notify_student"))


# ─────────────────────────────────────────────────────────────
# READ SIDE — used by the student notification bell
# ─────────────────────────────────────────────────────────────
def fetch_notifications(reg_number: str, limit: int = 30) -> List[Dict]:
    def _run():
        res = (
            get_client().table("notifications").select("*")
            .eq("student_reg", reg_number.strip().upper())
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    return safe_call(_run, default=[], log_label="fetch_notifications")


def unread_notification_count(reg_number: str) -> int:
    def _run():
        res = (
            get_client().table("notifications").select("id", count="exact")
            .eq("student_reg", reg_number.strip().upper())
            .eq("is_read", False)
            .execute()
        )
        return res.count or 0
    return safe_call(_run, default=0, log_label="unread_notification_count")


def mark_notification_read(notification_id: str) -> bool:
    def _run():
        get_client().table("notifications").update({"is_read": True}).eq("id", notification_id).execute()
        return True
    return bool(safe_call(_run, default=False, log_label="mark_notification_read"))


def mark_all_notifications_read(reg_number: str) -> bool:
    def _run():
        get_client().table("notifications").update({"is_read": True}) \
            .eq("student_reg", reg_number.strip().upper()).eq("is_read", False).execute()
        return True
    return bool(safe_call(_run, default=False, log_label="mark_all_notifications_read"))


# ─────────────────────────────────────────────────────────────
# REALTIME
#
# Streamlit re-runs the whole script top-to-bottom on every interaction
# and has no long-lived event loop of its own, so a raw asyncio websocket
# subscription (the way Supabase Realtime works over the wire) can't be
# "awaited" inside a normal Streamlit run. The supported, robust pattern
# is:
#
#   Supabase INSERT → Realtime (websocket, server-side) → this app polls
#   the *lightweight* unread-count/list endpoints on a short interval via
#   st.fragment(run_every=...), rather than reloading the whole page.
#
# That keeps the "realtime" work happening in Postgres/Supabase (not a
# spreadsheet), and keeps the UI update cheap and near-instant (a few
# seconds) without requiring a custom websocket bridge into Streamlit's
# threading model. See notifications_ui.py for the st.fragment usage,
# and README_SUPABASE_MIGRATION.md → "Known limitations" for the
# true-websocket alternative if you want to push this further.
# ─────────────────────────────────────────────────────────────
POLL_INTERVAL_SECONDS = 5
