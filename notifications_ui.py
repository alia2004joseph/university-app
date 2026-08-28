"""
notifications_ui.py — 🔔 Notification bell for the student dashboard.

Renders unread count + notification list, lets the student open an
announcement/material and mark notifications as read. Refreshes itself
every few seconds via st.fragment so new notifications show up without
a full page reload — see database/notifications.py for why this is the
right pattern inside Streamlit's execution model.
"""

import streamlit as st

from database.notifications import (
    fetch_notifications, unread_notification_count,
    mark_notification_read, mark_all_notifications_read,
    POLL_INTERVAL_SECONDS,
)

_TYPE_ICON = {
    "announcement": "📢",
    "material": "📄",
    "timetable": "🗓️",
    "feedback_reply": "💬",
    "system": "🔔",
}


def _time_ago(iso_ts: str) -> str:
    if not iso_ts:
        return ""
    try:
        from datetime import datetime, timezone
        ts = datetime.fromisoformat(str(iso_ts).replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - ts
        secs = delta.total_seconds()
        if secs < 60:
            return "just now"
        if secs < 3600:
            return f"{int(secs // 60)} min ago"
        if secs < 86400:
            return f"{int(secs // 3600)} hr ago"
        return f"{int(secs // 86400)} day(s) ago"
    except Exception:
        return ""


@st.fragment(run_every=POLL_INTERVAL_SECONDS)
def render_notification_bell(reg_number: str, primary: str = "#1a56db"):
    """Call this once, near the top of the student dashboard."""
    count = unread_notification_count(reg_number)
    label = f"🔔 Notifications ({count})" if count else "🔔 Notifications"

    with st.popover(label, use_container_width=False):
        notifications = fetch_notifications(reg_number, limit=25)

        if not notifications:
            st.caption("You're all caught up — no notifications yet.")
            return

        if count:
            if st.button("Mark all as read", key=f"mark_all_read_{reg_number}", use_container_width=True):
                mark_all_notifications_read(reg_number)
                st.rerun()

        for n in notifications:
            icon = _TYPE_ICON.get(n.get("notification_type", "system"), "🔔")
            is_read = n.get("is_read", False)
            title = n.get("title", "Notification")
            message = n.get("message", "")
            when = _time_ago(n.get("created_at", ""))

            bg = "#f8fafc" if is_read else "#eff6ff"
            border = "#e2e8f0" if is_read else primary
            st.markdown(
                f"""
                <div style="background:{bg};border-left:3px solid {border};
                    padding:10px 12px;border-radius:8px;margin-bottom:8px;">
                    <div style="font-weight:{'500' if is_read else '700'};font-size:0.92rem;color:#0f172a;">
                        {icon} {title}
                    </div>
                    <div style="font-size:0.85rem;color:#475569;margin-top:2px;">{message}</div>
                    <div style="font-size:0.72rem;color:#94a3b8;margin-top:4px;">{when}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if not is_read:
                if st.button("Mark as read", key=f"notif_read_{n.get('id')}"):
                    mark_notification_read(n.get("id"))
                    st.rerun()
