"""database/announcements.py — Announcements (replaces 'Announcements' sheet).

Posting an announcement also fans out a `notifications` row to every
matching student in one step, so callers (class_rep.py / Superadmin.py)
don't need to change at all — see section 8/9 of the migration brief.
"""

from typing import Dict, List

from .supabase_client import get_client, safe_call, none_if_all, all_if_none
from .notifications import notify_students_for_announcement


def _row_to_ann_dict(row: Dict) -> Dict:
    return {
        "id": row.get("id", ""),
        "timestamp": row.get("created_at", ""),
        "text": row.get("content", ""),
        "priority": row.get("priority", "Normal"),
        "dept": all_if_none(row.get("department_code")),
        "year": all_if_none(row.get("year")),
    }


def fetch_announcements(dept: str = "ALL", year: str = "ALL") -> List[Dict]:
    def _run():
        client = get_client()
        q = client.table("announcements").select("*")
        d, y = none_if_all(dept), none_if_all(year)
        # Always include department/year-wide broadcasts (NULL) alongside
        # the specific scope, matching the old sheet's "ALL" semantics.
        if d:
            q = q.or_(f"department_code.eq.{d},department_code.is.null")
        if y:
            q = q.or_(f"year.eq.{y},year.is.null")
        res = q.order("created_at", desc=True).execute()
        return [_row_to_ann_dict(r) for r in (res.data or [])]
    return safe_call(_run, default=[], log_label="fetch_announcements")


def post_announcement(
    text: str, priority: str = "Normal", dept: str = "ALL", year: str = "ALL",
    notify_whatsapp: bool = False, created_by: str = "Class Rep",
) -> bool:
    def _run():
        client = get_client()
        row = client.table("announcements").insert({
            "title": "New Announcement" if priority != "Urgent" else "Urgent Announcement",
            "content": text.strip(),
            "priority": priority,
            "department_code": none_if_all(dept),
            "year": none_if_all(year),
                        "created_by": created_by,
        }).execute()
        if row.data:
            ann = row.data[0]
            notify_students_for_announcement(ann, dept=dept, year=year)
        return True
    return bool(safe_call(_run, default=False, log_label="post_announcement"))


def delete_announcement(text: str) -> bool:
    def _run():
        get_client().table("announcements").delete().eq("content", text.strip()).execute()
        return True
    return bool(safe_call(_run, default=False, log_label="delete_announcement"))
