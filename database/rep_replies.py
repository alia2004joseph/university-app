"""database/rep_replies.py — Class Rep replies to student feedback."""

from typing import Dict, List, Optional

from .supabase_client import get_client, safe_call, none_if_all
from .notifications import notify_student


def fetch_rep_replies(reg_number: Optional[str] = None, dept: str = "ALL", year: str = "ALL") -> List[Dict]:
    def _run():
        client = get_client()
        q = client.table("rep_replies").select("*")
        if reg_number:
            q = q.eq("reg_number", reg_number.strip().upper())
        d, y = none_if_all(dept), none_if_all(year)
        if d:
            q = q.eq("department_code", d)
        if y:
            q = q.eq("year", y)
        res = q.order("created_at", desc=True).execute()
        return res.data or []
    return safe_call(_run, default=[], log_label="fetch_rep_replies")


def post_rep_reply(reg_number: str, student_name: str, message: str, rep_name: str,
                    dept: str = "ALL", year: str = "ALL") -> bool:
    def _run():
        get_client().table("rep_replies").insert({
            "reg_number": reg_number.strip().upper(),
            "student_name": student_name.strip(),
            "rep_name": rep_name.strip(),
            "message": message.strip(),
            "department_code": none_if_all(dept),
            "year": none_if_all(year),
            "read_status": "Unread",
        }).execute()
        notify_student(
            reg_number, "New Reply from Class Rep",
            message.strip()[:280], notification_type="feedback_reply",
        )
        return True
    return bool(safe_call(_run, default=False, log_label="post_rep_reply"))


def mark_rep_reply_read(timestamp: str, reg_number: str) -> bool:
    def _run():
        client = get_client()
        q = client.table("rep_replies").update({"read_status": "Read"}).eq("reg_number", reg_number.strip().upper())
        if timestamp:
            q = q.eq("created_at", timestamp)
        q.execute()
        return True
    return bool(safe_call(_run, default=False, log_label="mark_rep_reply_read"))
