"""
database/email_notify.py — Email notifications (optional secondary channel,
same pattern as database/whatsapp.py).

IMPORTANT BY DESIGN: emails are always short teasers with a link back to
the app — never the full announcement/material content. The goal (per
the product requirement) is for students to actually open the portal,
not to replace it with their inbox.

Uses plain SMTP (works with Gmail, Outlook, SendGrid SMTP relay, etc.) so
no extra paid service is required. Configure via Streamlit secrets:

    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL, APP_URL

If these aren't set, every function here just returns False/0 (logged,
never raised) — the in-app notification system and the rest of the app
keep working exactly as before.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from typing import Dict, List

from .supabase_client import get_client, safe_call, none_if_all, _get_secret

_APP_URL_FALLBACK = "your Smart University App"


def _smtp_config():
    host = _get_secret("SMTP_HOST")
    port = _get_secret("SMTP_PORT", "587")
    user = _get_secret("SMTP_USER")
    password = _get_secret("SMTP_PASSWORD")
    from_email = _get_secret("SMTP_FROM_EMAIL", user)
    if not (host and user and password and from_email):
        return None
    return {
        "host": host, "port": int(port), "user": user,
        "password": password, "from_email": from_email,
    }


def is_email_configured() -> bool:
    return _smtp_config() is not None


def _app_url() -> str:
    return _get_secret("APP_URL", _APP_URL_FALLBACK)


def _send_raw_email(to_email: str, subject: str, body: str) -> bool:
    cfg = _smtp_config()
    if not cfg or not to_email:
        return False
    try:
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = cfg["from_email"]
        msg["To"] = to_email

        context = ssl.create_default_context()
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
            server.starttls(context=context)
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["from_email"], [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"[email_notify] send error to {to_email}: {e}")
        return False


def _teaser_body(title: str, snippet: str, kind_label: str) -> str:
    link = _app_url()
    snippet = (snippet or "").strip()
    if len(snippet) > 140:
        snippet = snippet[:140].rstrip() + "…"
    return (
        f"{title}\n\n"
        f"{snippet}\n\n"
        f"This is just a preview — please open the Smart University App to "
        f"read the full {kind_label} and stay up to date:\n{link}\n\n"
        f"— Smart University App"
    )


def notify_students_email_for_announcement(announcement_row: Dict, dept: str = "ALL", year: str = "ALL") -> int:
    """Send a short 'new announcement — open the app' teaser email to every
    matching student who has an email on file. Never includes the full
    announcement text."""
    def _run():
        if not is_email_configured():
            return 0
        client = get_client()
        q = client.table("students").select("email")
        d, y = none_if_all(dept), none_if_all(year)
        if d:
            q = q.eq("department_code", d)
        if y:
            q = q.eq("year", y)
        res = q.execute()

        subject = "📢 New Announcement — Smart University App"
        body = _teaser_body(
            announcement_row.get("title") or "New Announcement",
            announcement_row.get("content", ""),
            "announcement",
        )
        sent = 0
        for row in (res.data or []):
            email = (row.get("email") or "").strip()
            if email and _send_raw_email(email, subject, body):
                sent += 1
        return sent
    return safe_call(_run, default=0, log_label="notify_students_email_for_announcement")


def notify_students_email_for_material(material_row: Dict, dept: str = "ALL", year: str = "ALL") -> int:
    def _run():
        if not is_email_configured():
            return 0
        client = get_client()
        q = client.table("students").select("email")
        d, y = none_if_all(dept), none_if_all(year)
        if d:
            q = q.eq("department_code", d)
        if y:
            q = q.eq("year", y)
        res = q.execute()

        subject = "📄 New Learning Material — Smart University App"
        body = _teaser_body(
            "New Learning Material",
            material_row.get("title", "A new material was uploaded."),
            "material",
        )
        sent = 0
        for row in (res.data or []):
            email = (row.get("email") or "").strip()
            if email and _send_raw_email(email, subject, body):
                sent += 1
        return sent
    return safe_call(_run, default=0, log_label="notify_students_email_for_material")


def notify_student_email(reg_number: str, title: str, teaser: str, kind_label: str = "update") -> bool:
    """Single-student teaser email (e.g. a feedback reply)."""
    def _run():
        if not is_email_configured():
            return False
        client = get_client()
        res = client.table("students").select("email") \
            .eq("reg_number", reg_number.strip().upper()).limit(1).execute()
        if not res.data or not res.data[0].get("email"):
            return False
        return _send_raw_email(res.data[0]["email"], f"🔔 {title} — Smart University App",
                                _teaser_body(title, teaser, kind_label))
    return bool(safe_call(_run, default=False, log_label="notify_student_email"))
