"""
database/read_receipts.py — Engagement tracking for announcements and course materials.
Allows Class Representatives and Admins to monitor exact student read status
and material access/download details with comprehensive student profiles.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from .supabase_client import get_client, safe_call, none_if_all

log = logging.getLogger("database.read_receipts")


def _format_timestamp(ts: Optional[str]) -> str:
    """Helper to format ISO timestamps into user-friendly strings."""
    if not ts:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        # Local representation
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return str(ts)


# ─────────────────────────────────────────────────────────────
# 1. ANNOUNCEMENT READ TRACKING
# ─────────────────────────────────────────────────────────────

def mark_announcement_read(student_reg: str, announcement_id: str = "", ann_text: str = "") -> bool:
    """
    Mark an announcement as read for a given student.
    Persists to `announcement_reads` table and syncs with `notifications`.
    """
    if not student_reg:
        return False
    reg_u = student_reg.strip().upper()

    def _run():
        client = get_client()
        target_ann_id = announcement_id

        # If ID is missing or text-based, resolve UUID from content
        if not target_ann_id and ann_text:
            res = client.table("announcements").select("id").eq("content", ann_text).limit(1).execute()
            if res.data:
                target_ann_id = res.data[0]["id"]

        # If we have a valid announcement ID
        if target_ann_id:
            # 1. Upsert into announcement_reads
            try:
                client.table("announcement_reads").upsert(
                    {
                        "announcement_id": target_ann_id,
                        "student_reg": reg_u,
                        "read_at": datetime.now(timezone.utc).isoformat()
                    },
                    on_conflict="announcement_id,student_reg"
                ).execute()
            except Exception as e:
                log.warning("Could not write to announcement_reads table (falling back to notifications): %s", e)

            # 2. Also mark corresponding notification row as read if present
            try:
                client.table("notifications").update({"is_read": True})\
                    .eq("student_reg", reg_u)\
                    .eq("announcement_id", target_ann_id)\
                    .execute()
            except Exception:
                pass

            return True

        return False

    return bool(safe_call(_run, default=False, log_label="mark_announcement_read"))


def get_student_read_announcement_ids(student_reg: str) -> Set[str]:
    """
    Fetch all announcement IDs marked as read by a student.
    Combines records from `announcement_reads` and `notifications`.
    """
    if not student_reg:
        return set()
    reg_u = student_reg.strip().upper()

    def _run():
        client = get_client()
        read_ids = set()

        # Check announcement_reads
        try:
            res = client.table("announcement_reads").select("announcement_id").eq("student_reg", reg_u).execute()
            for r in (res.data or []):
                if r.get("announcement_id"):
                    read_ids.add(str(r["announcement_id"]))
        except Exception:
            pass

        # Check notifications where notification_type = 'announcement' and is_read = True
        try:
            res_notif = client.table("notifications").select("announcement_id")\
                .eq("student_reg", reg_u)\
                .eq("is_read", True)\
                .not_.is_("announcement_id", "null")\
                .execute()
            for r in (res_notif.data or []):
                if r.get("announcement_id"):
                    read_ids.add(str(r["announcement_id"]))
        except Exception:
            pass

        return read_ids

    return safe_call(_run, default=set(), log_label="get_student_read_announcement_ids")


def get_announcement_read_analytics(
    announcement_id: str = "",
    dept: str = "ALL",
    year: str = "ALL",
    ann_text: str = ""
) -> Dict:
    """
    Calculate full read receipts for an announcement:
    Returns total count, read count, unread count, and full student details for both.
    """
    def _run():
        client = get_client()
        target_id = announcement_id

        # Resolve ID if needed
        if not target_id and ann_text:
            res_ann = client.table("announcements").select("id, department_code, year").eq("content", ann_text).limit(1).execute()
            if res_ann.data:
                target_id = res_ann.data[0]["id"]
                if dept == "ALL" and res_ann.data[0].get("department_code"):
                    dept = res_ann.data[0]["department_code"]
                if year == "ALL" and res_ann.data[0].get("year"):
                    year = res_ann.data[0]["year"]

        # Fetch target students in scope
        q_stud = client.table("students").select(
            "reg_number, student_name, course_code, contact, whatsapp_phone, assigned_group, email, avatar_url, department_code, year"
        )
        d = none_if_all(dept)
        y = none_if_all(year)
        if d:
            q_stud = q_stud.eq("department_code", d)
        if y:
            q_stud = q_stud.eq("year", y)
        stud_res = q_stud.order("student_name").execute()
        all_students = stud_res.data or []

        # Fetch read records
        read_records: Dict[str, str] = {}  # reg_number -> read_at

        if target_id:
            try:
                r_res = client.table("announcement_reads").select("student_reg, read_at").eq("announcement_id", target_id).execute()
                for r in (r_res.data or []):
                    reg = str(r.get("student_reg", "")).strip().upper()
                    if reg:
                        read_records[reg] = r.get("read_at", "")
            except Exception:
                pass

            # Fallback/merge with notifications table
            try:
                n_res = client.table("notifications").select("student_reg, is_read, created_at")\
                    .eq("announcement_id", target_id)\
                    .eq("is_read", True)\
                    .execute()
                for n in (n_res.data or []):
                    reg = str(n.get("student_reg", "")).strip().upper()
                    if reg and reg not in read_records:
                        read_records[reg] = n.get("created_at", "")
            except Exception:
                pass

        read_list = []
        unread_list = []

        for s in all_students:
            s_reg = str(s.get("reg_number", "")).strip().upper()
            student_info = {
                "reg_number": s.get("reg_number", ""),
                "name": s.get("student_name", "Unknown"),
                "email": s.get("email", "") or "",
                "contact": s.get("contact", "") or "",
                "whatsapp_phone": s.get("whatsapp_phone", "") or s.get("contact", "") or "",
                "course_code": s.get("course_code", "N/A"),
                "group": s.get("assigned_group", "Unassigned"),
                "department": s.get("department_code", ""),
                "year": s.get("year", ""),
                "avatar": s.get("avatar_url", "") or "",
            }

            if s_reg in read_records:
                student_info["read_at"] = _format_timestamp(read_records[s_reg])
                read_list.append(student_info)
            else:
                unread_list.append(student_info)

        total_count = len(all_students)
        read_count = len(read_list)
        unread_count = len(unread_list)
        pct = round((read_count / total_count * 100), 1) if total_count > 0 else 0.0

        return {
            "announcement_id": target_id,
            "total_students": total_count,
            "read_count": read_count,
            "unread_count": unread_count,
            "read_percentage": pct,
            "read_students": read_list,
            "unread_students": unread_list,
        }

    return safe_call(
        _run,
        default={
            "announcement_id": announcement_id,
            "total_students": 0,
            "read_count": 0,
            "unread_count": 0,
            "read_percentage": 0.0,
            "read_students": [],
            "unread_students": [],
        },
        log_label="get_announcement_read_analytics"
    )


# ─────────────────────────────────────────────────────────────
# 2. COURSE MATERIAL ACCESS TRACKING
# ─────────────────────────────────────────────────────────────

def mark_material_accessed(
    student_reg: str,
    material_id: str = "",
    file_name: str = "",
    action: str = "view"
) -> bool:
    """
    Log that a student has checked, previewed, downloaded, or studied a course material.
    """
    if not student_reg:
        return False
    reg_u = student_reg.strip().upper()

    def _run():
        client = get_client()
        target_mat_id = material_id

        # Resolve ID from filename if missing
        if not target_mat_id and file_name:
            res_m = client.table("materials").select("id").eq("title", file_name).limit(1).execute()
            if res_m.data:
                target_mat_id = res_m.data[0]["id"]

        if target_mat_id:
            # 1. Upsert into material_access_logs
            try:
                client.table("material_access_logs").upsert(
                    {
                        "material_id": target_mat_id,
                        "student_reg": reg_u,
                        "action_type": action,
                        "accessed_at": datetime.now(timezone.utc).isoformat()
                    },
                    on_conflict="material_id,student_reg"
                ).execute()
            except Exception as e:
                log.warning("Could not write to material_access_logs: %s", e)

            # 2. Update notification row if present
            try:
                client.table("notifications").update({"is_read": True})\
                    .eq("student_reg", reg_u)\
                    .eq("material_id", target_mat_id)\
                    .execute()
            except Exception:
                pass

            return True

        return False

    return bool(safe_call(_run, default=False, log_label="mark_material_accessed"))


def get_material_access_analytics(
    material_id: str = "",
    dept: str = "ALL",
    year: str = "ALL",
    file_name: str = ""
) -> Dict:
    """
    Calculate full access receipts for a course material:
    Returns total count, accessed count, unaccessed count, and full student details for both.
    """
    def _run():
        client = get_client()
        target_id = material_id

        if not target_id and file_name:
            res_m = client.table("materials").select("id, department_code, year").eq("title", file_name).limit(1).execute()
            if res_m.data:
                target_id = res_m.data[0]["id"]
                if dept == "ALL" and res_m.data[0].get("department_code"):
                    dept = res_m.data[0]["department_code"]
                if year == "ALL" and res_m.data[0].get("year"):
                    year = res_m.data[0]["year"]

        # Fetch target students
        q_stud = client.table("students").select(
            "reg_number, student_name, course_code, contact, whatsapp_phone, assigned_group, email, avatar_url, department_code, year"
        )
        d = none_if_all(dept)
        y = none_if_all(year)
        if d:
            q_stud = q_stud.eq("department_code", d)
        if y:
            q_stud = q_stud.eq("year", y)
        stud_res = q_stud.order("student_name").execute()
        all_students = stud_res.data or []

        access_records: Dict[str, Dict] = {}  # reg_number -> {accessed_at, action_type}

        if target_id:
            try:
                a_res = client.table("material_access_logs").select("student_reg, action_type, accessed_at").eq("material_id", target_id).execute()
                for r in (a_res.data or []):
                    reg = str(r.get("student_reg", "")).strip().upper()
                    if reg:
                        access_records[reg] = {
                            "action": r.get("action_type", "view"),
                            "accessed_at": r.get("accessed_at", "")
                        }
            except Exception:
                pass

            # Fallback/merge with notifications table
            try:
                n_res = client.table("notifications").select("student_reg, is_read, created_at")\
                    .eq("material_id", target_id)\
                    .eq("is_read", True)\
                    .execute()
                for n in (n_res.data or []):
                    reg = str(n.get("student_reg", "")).strip().upper()
                    if reg and reg not in access_records:
                        access_records[reg] = {
                            "action": "checked",
                            "accessed_at": n.get("created_at", "")
                        }
            except Exception:
                pass

        accessed_list = []
        unaccessed_list = []

        action_labels = {
            "download": "⬇️ Downloaded",
            "preview": "👁️ Previewed",
            "ai_study": "🤖 AI Studied",
            "view": "👁️ Viewed",
            "checked": "✅ Checked",
        }

        for s in all_students:
            s_reg = str(s.get("reg_number", "")).strip().upper()
            student_info = {
                "reg_number": s.get("reg_number", ""),
                "name": s.get("student_name", "Unknown"),
                "email": s.get("email", "") or "",
                "contact": s.get("contact", "") or "",
                "whatsapp_phone": s.get("whatsapp_phone", "") or s.get("contact", "") or "",
                "course_code": s.get("course_code", "N/A"),
                "group": s.get("assigned_group", "Unassigned"),
                "department": s.get("department_code", ""),
                "year": s.get("year", ""),
                "avatar": s.get("avatar_url", "") or "",
            }

            if s_reg in access_records:
                rec = access_records[s_reg]
                raw_act = rec.get("action", "view")
                student_info["action"] = action_labels.get(raw_act, raw_act.title())
                student_info["accessed_at"] = _format_timestamp(rec.get("accessed_at", ""))
                accessed_list.append(student_info)
            else:
                unaccessed_list.append(student_info)

        total_count = len(all_students)
        acc_count = len(accessed_list)
        unacc_count = len(unaccessed_list)
        pct = round((acc_count / total_count * 100), 1) if total_count > 0 else 0.0

        return {
            "material_id": target_id,
            "total_students": total_count,
            "accessed_count": acc_count,
            "unaccessed_count": unacc_count,
            "accessed_percentage": pct,
            "accessed_students": accessed_list,
            "unaccessed_students": unaccessed_list,
        }

    return safe_call(
        _run,
        default={
            "material_id": material_id,
            "total_students": 0,
            "accessed_count": 0,
            "unaccessed_count": 0,
            "accessed_percentage": 0.0,
            "accessed_students": [],
            "unaccessed_students": [],
        },
        log_label="get_material_access_analytics"
    )
