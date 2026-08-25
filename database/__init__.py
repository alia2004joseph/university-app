"""
database/__init__.py — Supabase-backed database facade.

This package replaces the old single `database.py` (Google Sheets +
Apps Script webhooks). `SupabaseDatabaseManager` below exposes the exact
same public methods/signatures the rest of the app (app.py, student.py,
class_rep.py, Superadmin.py, ai_engine.py) already calls through `db.*`,
so none of those files need to know the backend changed.

`SheetDatabaseManager` is kept as an alias purely so old imports/
references to that name keep working without edits.

Actual logic lives in focused sibling modules:
    supabase_client.py  — connection, hashing, error-safety helpers
    departments.py       announcements.py     materials.py
    students.py          feedback.py          rep_replies.py
    reps.py               timetable.py         notifications.py
    whatsapp.py           chat.py              ai_memory.py
    config_store.py       slots.py             admin_tools.py
"""

from typing import Dict, List, Optional, Union

import pandas as pd

from .supabase_client import get_client, is_configured, SupabaseUnavailableError  # noqa: F401
from . import departments as _departments
from . import students as _students
from . import announcements as _announcements
from . import materials as _materials
from . import feedback as _feedback
from . import rep_replies as _rep_replies
from . import reps as _reps
from . import timetable as _timetable
from . import notifications as _notifications
from . import whatsapp as _whatsapp
from . import chat as _chat
from . import ai_memory as _ai_memory
from . import config_store as _config_store
from . import slots as _slots
from . import admin_tools as _admin_tools

ROSTER_COLUMNS = _students.ROSTER_COLUMNS


class SupabaseDatabaseManager:
    """Database manager for the Supabase-backed application."""

    def __init__(self):
        # Touching get_client() here would raise before the UI can show a
        # friendly banner, so connectivity is only checked lazily per call
        # (see supabase_client.safe_call).
        pass

    def is_connected(self) -> bool:
        return is_configured()

    # ── ROSTER / STUDENTS ───────────────────────────────────────
    def fetch_roster(self, dept: str = "ALL", year: str = "ALL") -> pd.DataFrame:
        rows = _students.fetch_roster_rows(dept=dept, year=year)
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=ROSTER_COLUMNS)

    def fetch_all_roster(self) -> pd.DataFrame:
        return self.fetch_roster(dept="ALL", year="ALL")

    def register_student(self, name, reg, code, contact, dept, year, pin=None, whatsapp_phone="", email="") -> Dict:
        return _students.register_student(name, reg, code, contact, dept, year, pin, whatsapp_phone, email)

    def delete_student(self, name: str) -> Dict:
        return _students.delete_student(name)

    def save_group_allocations(self, allocations_dict: Dict) -> Dict:
        return _students.save_group_allocations(allocations_dict)

    def assign_group(self, reg_number_or_name: str, group_name: str) -> bool:
        return _students.assign_group(reg_number_or_name, group_name)

    def save_course_unit_groups(self, dept: str, year: str, course_groups: Dict) -> Dict:
        return _students.save_course_unit_groups(dept, year, course_groups)

    def fetch_course_unit_groups(self, student_name: str, dept: str = "ALL", year: str = "ALL") -> Dict:
        return _students.fetch_course_unit_groups(student_name, dept, year)

    def update_student_course_groups(self, student_reg: str, course_groups: Dict, dept: str = "", year: str = "") -> Dict:
        return _students.update_student_course_groups(student_reg, course_groups, dept, year)

    def update_contact(self, reg_number: str, new_contact: str) -> bool:
        return _students.update_contact(reg_number, new_contact)

    def update_whatsapp(self, reg_number: str, phone: str, apikey: str) -> bool:
        return _students.update_whatsapp(reg_number, phone, apikey)

    def update_email(self, reg_number: str, new_email: str) -> Dict:
        return _students.update_email(reg_number, new_email)

    def verify_student(self, reg_number: str, pin: str) -> Dict:
        return _students.verify_student(reg_number, pin)

    def set_pin(self, reg_number: str, new_pin: str) -> bool:
        return _students.set_pin(reg_number, new_pin)

    def reset_pin(self, reg_number: str, contact: str, new_pin: str) -> Dict:
        return _students.reset_pin(reg_number, contact, new_pin)

    # ── ANNOUNCEMENTS ───────────────────────────────────────────
    def fetch_announcements(self, dept: str = "ALL", year: str = "ALL") -> List:
        return _announcements.fetch_announcements(dept, year)

    def fetch_all_announcements(self) -> List:
        return _announcements.fetch_announcements("ALL", "ALL")

    def post_announcement(self, text: str, priority: str = "Normal", dept: str = "ALL",
                           year: str = "ALL", notify_whatsapp: bool = False) -> bool:
        return _announcements.post_announcement(text, priority, dept, year, notify_whatsapp)

    def delete_announcement(self, text: str) -> bool:
        return _announcements.delete_announcement(text)

    def broadcast_announcement(self, text: str, priority: str = "Normal") -> bool:
        return self.post_announcement(text, priority, dept="ALL", year="ALL")

    # ── MATERIALS ────────────────────────────────────────────────
    def fetch_materials(self, dept: str = "ALL", year: str = "ALL") -> List:
        return _materials.fetch_materials(dept, year)

    def fetch_file_bytes(self, url: str) -> bytes:
        return _materials.fetch_file_bytes(url)

    def upload_material(self, file_bytes, file_name: str, mime_type: str, dept: str = "ALL",
                         year: str = "ALL", notify_whatsapp: bool = False) -> bool:
        return _materials.upload_material(file_bytes, file_name, mime_type, dept, year, notify_whatsapp)

    def delete_material(self, file_name: str) -> bool:
        return _materials.delete_material(file_name)

    # ── FEEDBACK ─────────────────────────────────────────────────
    def fetch_feedback(self, dept: str = "ALL", year: str = "ALL") -> List:
        return _feedback.fetch_feedback(dept, year)

    def fetch_all_feedback(self) -> List:
        return _feedback.fetch_feedback("ALL", "ALL")

    def submit_feedback(self, reg_num: str, name: str, message: str, dept: str = "ALL", year: str = "ALL") -> bool:
        return _feedback.submit_feedback(reg_num, name, message, dept, year)

    def delete_feedback(self, timestamp: str, reg_number: str) -> bool:
        return _feedback.delete_feedback(timestamp, reg_number)

    def delete_all_feedback(self, reg_number: str) -> bool:
        return _feedback.delete_all_feedback(reg_number)

    def update_feedback_status(self, timestamp: str, reg_number: str, status: str = "Reviewed") -> bool:
        return _feedback.update_feedback_status(timestamp, reg_number, status)

    # ── REP REPLIES ─────────────────────────────────────────────
    def fetch_rep_replies(self, reg_number: Optional[str] = None, dept: str = "ALL", year: str = "ALL") -> List:
        return _rep_replies.fetch_rep_replies(reg_number, dept, year)

    def post_rep_reply(self, reg_number: str, student_name: str, message: str, rep_name: str,
                        dept: str = "ALL", year: str = "ALL") -> bool:
        return _rep_replies.post_rep_reply(reg_number, student_name, message, rep_name, dept, year)

    def mark_rep_reply_read(self, timestamp: str, reg_number: str) -> bool:
        return _rep_replies.mark_rep_reply_read(timestamp, reg_number)

    # ── REP ACCOUNTS ────────────────────────────────────────────
    def fetch_reps(self) -> List:
        return _reps.fetch_reps()

    def verify_rep(self, dept: str, year: str, password: str) -> Dict:
        return _reps.verify_rep(dept, year, password)

    def assign_rep(self, dept: str, year: str, rep_name: str, rep_reg: str, password: str) -> bool:
        return _reps.assign_rep(dept, year, rep_name, rep_reg, password)

    def delete_rep(self, dept: str, year: str) -> bool:
        return _reps.delete_rep(dept, year)

    def change_rep_password(self, dept: str, year: str, old_password: str, new_password: str) -> Dict:
        return _reps.change_rep_password(dept, year, old_password, new_password)

    # ── TIMETABLE ────────────────────────────────────────────────
    def fetch_timetable(self, dept: str = "ALL", year: str = "ALL") -> List:
        return _timetable.fetch_timetable(dept, year)

    def add_timetable_entry(self, dept: str, year: str, day: str, time: str, course: str,
                             lecturer: str = "", color: str = "", entry_type: str = "Weekly") -> bool:
        return _timetable.add_timetable_entry(dept, year, day, time, course, lecturer, color, entry_type)

    def delete_timetable_entry(self, dept: str, year: str, day: str, time: str) -> bool:
        return _timetable.delete_timetable_entry(dept, year, day, time)

    def clear_timetable(self, dept: str, year: str) -> bool:
        return _timetable.clear_timetable(dept, year)

    # ── WHATSAPP (optional secondary channel) ──────────────────
    def notify_student_whatsapp(self, reg_number: str, message: str) -> bool:
        return _whatsapp.notify_student_whatsapp(reg_number, message)

    def notify_class_whatsapp(self, dept: str, year: str, message: str) -> int:
        return _whatsapp.broadcast_whatsapp(dept, year, message)

    def broadcast_whatsapp(self, dept: str, year: str, message: str) -> int:
        return _whatsapp.broadcast_whatsapp(dept, year, message)

    # ── CHAT HISTORY ────────────────────────────────────────────
    def save_chat_message(self, reg_number: str, role: str, message: str) -> bool:
        return _chat.save_chat_message(reg_number, role, message)

    def get_chat_history(self, reg_number: str, limit: int = 20) -> List:
        return _chat.get_chat_history(reg_number, limit)

    def clear_chat_history(self, reg_number: str) -> bool:
        return _chat.clear_chat_history(reg_number)

    # ── DEPARTMENTS ─────────────────────────────────────────────
    def fetch_departments(self) -> List:
        return _departments.fetch_departments()

    def add_department(self, code: str, name: str, color: str, light: str, courses: str) -> bool:
        ok = _departments.add_department(code, name, color, light, courses)
        if ok:
            from config import load_departments
            load_departments.clear()
        return ok

    def update_department(self, code: str, name: str, color: str, light: str, courses: str) -> bool:
        ok = _departments.update_department(code, name, color, light, courses)
        if ok:
            from config import load_departments
            load_departments.clear()
        return ok

    def delete_department(self, code: str) -> Dict:
        result = _departments.delete_department(code)
        if result.get("status") == "success":
            from config import load_departments
            load_departments.clear()
        return result

    # ── ADMIN DEV TOOLS (sheet manager / function library) ─────
    def list_sheets(self) -> List:
        return _admin_tools.list_sheets()

    def create_sheet(self, sheet_name: str, headers: List = None) -> Dict:
        return _admin_tools.create_sheet(sheet_name, headers)

    def rename_sheet(self, old_name: str, new_name: str) -> Dict:
        return _admin_tools.rename_sheet(old_name, new_name)

    def clear_sheet(self, sheet_name: str) -> Dict:
        return _admin_tools.clear_sheet(sheet_name)

    def delete_sheet(self, sheet_name: str) -> Dict:
        return _admin_tools.delete_sheet(sheet_name)

    def get_all_config(self) -> Dict:
        return _config_store.get_all_config()

    def get_config_value(self, key: str) -> Optional[str]:
        return _config_store.get_config_value(key)

    def set_config(self, key: str, value: str, description: str = "") -> Dict:
        return _config_store.set_config(key, value, description)

    def read_sheet(self, sheet_name: str, filter_key: str = "", filter_value: str = "") -> Union[List, Dict]:
        return _admin_tools.read_sheet(sheet_name, filter_key, filter_value)

    def write_row(self, sheet_name: str, row: List, add_timestamp: bool = True) -> Dict:
        return _admin_tools.write_row(sheet_name, row, add_timestamp)

    def delete_row(self, sheet_name: str, match_key: str, match_value: str, delete_all: bool = False) -> Dict:
        return _admin_tools.delete_row(sheet_name, match_key, match_value, delete_all)

    def list_functions(self) -> List:
        return _admin_tools.list_functions()

    def save_function(self, name: str, script: str, description: str = "") -> Dict:
        return _admin_tools.save_function(name, script, description)

    def run_function(self, name: str, params: Dict = None) -> Dict:
        return _admin_tools.run_function(name, params)

    def call_function(self, name: str, params: dict = None) -> dict:
        return _admin_tools.call_function(name, params)

    # ── SLOT SYSTEM ─────────────────────────────────────────────
    def get_active_slots(self, dept: str, year: str, audience: str = "student") -> List:
        return _slots.get_active_slots(dept, year, audience)

    def get_all_slots(self, audience: str = "student") -> List:
        return _slots.get_all_slots(audience)

    def save_slot(self, slot_data: Dict, audience: str = "student") -> Dict:
        return _slots.save_slot(slot_data, audience)

    def delete_slot(self, slot_id: str, audience: str = "student") -> Dict:
        return _slots.delete_slot(slot_id, audience)

    def toggle_slot(self, slot_id: str, active: bool, audience: str = "student") -> Dict:
        return _slots.toggle_slot(slot_id, active, audience)

    # ── MASTER AI MEMORY ────────────────────────────────────────
    def save_master_ai_memory(self, mem_type: str, key: str, value: str) -> bool:
        return _ai_memory.save_master_ai_memory(mem_type, key, value)

    def load_master_ai_memory(self, mem_type: str = None) -> list:
        return _ai_memory.load_master_ai_memory(mem_type)

    def delete_master_ai_memory(self, mem_type: str, key: str) -> bool:
        return _ai_memory.delete_master_ai_memory(mem_type, key)

    def clear_master_ai_memory(self, mem_type: str) -> bool:
        return _ai_memory.clear_master_ai_memory(mem_type)

    # ── NOTIFICATIONS (new — see database/notifications.py) ─────
    def fetch_notifications(self, reg_number: str, limit: int = 30) -> List:
        return _notifications.fetch_notifications(reg_number, limit)

    def unread_notification_count(self, reg_number: str) -> int:
        return _notifications.unread_notification_count(reg_number)

    def mark_notification_read(self, notification_id: str) -> bool:
        return _notifications.mark_notification_read(notification_id)

    def mark_all_notifications_read(self, reg_number: str) -> bool:
        return _notifications.mark_all_notifications_read(reg_number)


# Backward-compatible alias — old code imports `SheetDatabaseManager`.
SheetDatabaseManager = SupabaseDatabaseManager
