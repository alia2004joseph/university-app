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

def notify_students_email_for_group_allocation(allocations_dict: Dict, group_name_override: str = "", dept: str = "ALL", year: str = "ALL") -> int:
    """Send notification email to students when assigned to a group."""
    def _run():
        if not is_email_configured():
            return 0
        client = get_client()
        sent = 0
        subject = "👥 Group Allocation Update — Smart University App"
        for key, grp_val in allocations_dict.items():
            clean_key = str(key).strip()
            group_title = group_name_override or str(grp_val).strip()
            is_reg = any(c.isdigit() for c in clean_key) or ("/" in clean_key)
            q = client.table("students").select("student_name, email, reg_number")
            if is_reg:
                res = q.eq("reg_number", clean_key.upper()).limit(1).execute()
            else:
                res = q.eq("student_name", clean_key).limit(1).execute()
            if res.data and res.data[0].get("email"):
                student_info = res.data[0]
                student_email = student_info["email"].strip()
                student_name = student_info.get("student_name", "Student")
                body = (
                    f"Hello {student_name},\n\n"
                    f"You have been assigned to: {group_title}\n\n"
                    f"Open the Smart University App to view your fellow group members and their contact details:\n"
                    f"{_app_url()}\n\n"
                    f"— Smart University App"
                )
                if _send_raw_email(student_email, subject, body):
                    sent += 1
        return sent
    return safe_call(_run, default=0, log_label="notify_students_email_for_group_allocation")



def notify_rep_email_for_student_message(
    student_name: str,
    reg_number: str,
    message: str,
    dept: str = "ALL",
    year: str = "ALL"
) -> bool:
    """Send a full email notification to the Class Rep containing the complete
    student private message/inquiry and student identification details."""
    def _run():
        if not is_email_configured():
            return False
        from .reps import get_rep_email
        rep_email = get_rep_email(dept, year)
        if not rep_email:
            return False

        # Retrieve student details (email, course code) if available
        student_email = ""
        student_course = ""
        try:
            client = get_client()
            res = client.table("students").select("email, course_code").eq("reg_number", reg_number.strip().upper()).limit(1).execute()
            if res.data and res.data[0]:
                student_email = str(res.data[0].get("email") or "").strip()
                student_course = str(res.data[0].get("course_code") or "").strip()
        except Exception:
            pass

        email_line = f"• Student Email: {student_email}\n" if student_email else ""
        course_line = f"• Course Code: {student_course}\n" if student_course else ""

        subject = f"💬 Private Message from {student_name} ({reg_number}) — Smart University App"
        body = (
            f"Dear Class Representative,\n\n"
            f"You have received a new private message from a student in your class:\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"STUDENT DETAILS\n"
            f"• Name: {student_name}\n"
            f"• Registration Number: {reg_number}\n"
            f"• Department: {dept}\n"
            f"• Year of Study: {year}\n"
            f"{course_line}"
            f"{email_line}"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"FULL MESSAGE CONTENT:\n"
            f"\"{message.strip()}\"\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"To reply directly to this student via the portal, please log in to your Class Rep workspace:\n"
            f"{_app_url()}\n\n"
            f"— Smart University System"
        )
        return _send_raw_email(rep_email, subject, body)

    return bool(safe_call(_run, default=False, log_label="notify_rep_email_for_student_message"))
