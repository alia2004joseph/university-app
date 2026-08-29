"""database/feedback.py — Student → Class Rep feedback (replaces 'Feedback' sheet)."""

from typing import Dict, List

from .supabase_client import get_client, safe_call, none_if_all

def fetch_feedback(dept: str = "ALL", year: str = "ALL") -> List:
    """
    Returns feedback shaped like the legacy Sheets rows the UI already
    expects: [timestamp, reg_number, student_name, status, message,
    department_code, year] — every caller in student.py/class_rep.py/
    Superadmin.py unpacks feedback by these exact positions.
    """
    def _run():
        client = get_client()
        q = client.table("feedback").select("*")
        d, y = none_if_all(dept), none_if_all(year)
        if d:
            q = q.eq("department_code", d)
        if y:
            q = q.eq("year", y)
        res = q.order("created_at", desc=True).execute()
        rows = res.data or []
        return [
            [
                r.get("created_at", ""),
                r.get("reg_number", ""),
                r.get("student_name", ""),
                r.get("status", "Pending"),
                r.get("message", ""),
                r.get("department_code") or "ALL",
                r.get("year") or "ALL",
            ]
            for r in rows
        ]
    return safe_call(_run, default=[], log_label="fetch_feedback")


def submit_feedback(reg_num: str, name: str, message: str, dept: str = "ALL", year: str = "ALL") -> bool:
    def _run():
        get_client().table("feedback").insert({
            "reg_number": reg_num.strip().upper(),
            "student_name": name.strip(),
            "message": message.strip(),
            "department_code": none_if_all(dept),
            "year": none_if_all(year),
            "status": "Pending",
        }).execute()

        # Notify the Class Rep with the FULL student message and complete details
        try:
            from .email_notify import notify_rep_email_for_student_message
            notify_rep_email_for_student_message(
                student_name=name.strip(),
                reg_number=reg_num.strip().upper(),
                message=message.strip(),
                dept=dept,
                year=year
            )
        except Exception as e:
            print(f"[feedback] rep email notification failed (non-fatal): {e}")

        return True
    return bool(safe_call(_run, default=False, log_label="submit_feedback"))


def delete_feedback(timestamp: str, reg_number: str) -> bool:
    def _run():
        client = get_client()
        q = client.table("feedback").delete().eq("reg_number", reg_number.strip().upper())
        if timestamp:
            q = q.eq("created_at", timestamp)
        q.execute()
        return True
    return bool(safe_call(_run, default=False, log_label="delete_feedback"))


def delete_all_feedback(reg_number: str) -> bool:
    def _run():
        get_client().table("feedback").delete().eq("reg_number", reg_number.strip().upper()).execute()
        return True
    return bool(safe_call(_run, default=False, log_label="delete_all_feedback"))


def update_feedback_status(timestamp: str, reg_number: str, status: str = "Reviewed") -> bool:
    def _run():
        client = get_client()
        q = client.table("feedback").update({"status": status}).eq("reg_number", reg_number.strip().upper())
        if timestamp:
            q = q.eq("created_at", timestamp)
        q.execute()
        return True
    return bool(safe_call(_run, default=False, log_label="update_feedback_status"))