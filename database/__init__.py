"""
database/__init__.py — Unified Database Manager interface.
Dispatches to modular Supabase services under database/*.
"""
from typing import Dict, List, Optional, Union
from . import students as _students
from . import reps as _reps
from . import announcements as _announcements
from . import materials as _materials
from . import feedback as _feedback
from . import rep_replies as _rep_replies
from . import timetable as _timetable
from . import chat as _chat
from . import departments as _departments
from . import admin_tools as _admin_tools
from . import slots as _slots
from . import ai_memory as _ai_memory
from . import config_store as _config_store
from . import notifications as _notifications
from . import avatars as _avatars


class SupabaseDatabaseManager:
    """Single entry point mirroring SheetDatabaseManager's public API."""

    # ── AVATARS / PROFILE PHOTOS ────────────────────────────────
    def upload_student_avatar(self, reg_number: str, file_bytes: bytes, mime_type: str = "image/jpeg") -> Optional[str]:
        return _avatars.upload_student_avatar(reg_number, file_bytes, mime_type)

    def delete_student_avatar(self, reg_number: str) -> bool:
        return _avatars.delete_student_avatar(reg_number)

    def upload_rep_avatar(self, dept: str, year: str, file_bytes: bytes, mime_type: str = "image/jpeg") -> Optional[str]:
        return _avatars.upload_rep_avatar(dept, year, file_bytes, mime_type)

    def delete_rep_avatar(self, dept: str, year: str) -> bool:
        return _avatars.delete_rep_avatar(dept, year)

    def upload_admin_avatar(self, file_bytes: bytes, mime_type: str = "image/jpeg", admin_id: str = "superadmin") -> Optional[str]:
        return _avatars.upload_admin_avatar(file_bytes, mime_type, admin_id)

    def get_admin_avatar(self, admin_id: str = "superadmin") -> str:
        return _avatars.get_admin_avatar(admin_id)

    def delete_admin_avatar(self, admin_id: str = "superadmin") -> bool:
        return _avatars.delete_admin_avatar(admin_id)

    def render_avatar_html(self, avatar_url: Optional[str], name: str, size: int = 42, color: str = "#1a56db", light: str = "#dbeafe", extra_css: str = "") -> str:
        return _avatars.render_avatar_html(avatar_url, name, size, color, light, extra_css)

    # ── STUDENTS / ROSTER ───────────────────────────────────────
    def fetch_roster(self, dept: str = "ALL", year: str = "ALL") -> List[Dict]:
        return _students.fetch_roster_rows(dept, year)

    def fetch_all_roster(self):
        from cache import cached_fetch_roster
        return cached_fetch_roster(dept="ALL", year="ALL")

    def register_student(
        self, name: str, reg: str, code: str, contact: str, dept: str, year: str,
        pin: Optional[str] = None, email: str = "",
        avatar_bytes: Optional[bytes] = None, avatar_mime: str = "image/jpeg"
    ) -> Dict:
        return _students.register_student(
            name, reg, code, contact, dept, year, pin, email, avatar_bytes, avatar_mime
        )

    def delete_student(self, name: str) -> Dict:
        return _students.delete_student(name)

    def save_group_allocations(self, allocations_dict: Dict) -> Dict:
        return _students.save_group_allocations(allocations_dict)

    def assign_group(self, reg_number_or_name: str, group_name: str) -> bool:
        return _students.assign_group(reg_number_or_name, group_name)

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

    def update_student_course_groups(self, student_reg: str, course_groups: Dict, dept: str = "", year: str = "") -> Dict:
        return _students.update_student_course_groups(student_reg, course_groups, dept, year)

    def save_course_unit_groups(self, dept: str, year: str, course_groups: Dict) -> Dict:
        return _students.save_course_unit_groups(dept, year, course_groups)

    def fetch_course_unit_groups(self, student_name: str, dept: str = "ALL", year: str = "ALL") -> Dict:
        return _students.fetch_course_unit_groups(student_name, dept, year)

    # ── ANNOUNCEMENTS ───────────────────────────────────────────
    def fetch_announcements(self, dept: str = "ALL", year: str = "ALL") -> List:
        return _announcements.fetch_announcements(dept, year)

    def fetch_all_announcements(self) -> List:
        return _announcements.fetch_announcements(dept="ALL", year="ALL")

    def broadcast_announcement(self, text: str, priority: str = "Normal") -> bool:
        return _announcements.post_announcement(text=text, dept="ALL", year="ALL", priority=priority, posted_by="Super Admin")

    def post_announcement(self, text: str, dept: str = "ALL", year: str = "ALL",
                           priority: str = "Normal", pinned: bool = False,
                           posted_by: str = "Class Rep") -> bool:
        return _announcements.post_announcement(text, dept, year, priority, pinned, posted_by)

    def delete_announcement(self, ann_id: str) -> bool:
        return _announcements.delete_announcement(ann_id)

    # ── MATERIALS ───────────────────────────────────────────────
    def fetch_materials(self, dept: str = "ALL", year: str = "ALL") -> List:
        return _materials.fetch_materials(dept, year)

    def fetch_all_materials(self) -> List:
        return _materials.fetch_materials(dept="ALL", year="ALL")

    def upload_material(self, file_bytes, file_name: str, mime_type: str,
                        dept: str = "ALL", year: str = "ALL",
                        title: str = "",
                        uploaded_by: str = "Class Rep") -> bool:
        return _materials.upload_material(file_bytes, file_name, mime_type, dept, year,
                                          title, uploaded_by)

    def delete_material(self, file_name: str) -> bool:
        return _materials.delete_material(file_name)

    def fetch_file_bytes(self, url: str) -> bytes:
        return _materials.fetch_file_bytes(url)

    # ── FEEDBACK / MESSAGES ─────────────────────────────────────
    def fetch_feedback(self, dept: str = "ALL", year: str = "ALL") -> List:
        return _feedback.fetch_feedback(dept, year)

    def fetch_all_feedback(self) -> List:
        return _feedback.fetch_feedback(dept="ALL", year="ALL")

    def submit_feedback(self, reg_number: str, student_name: str, message: str,
                        dept: str = "ALL", year: str = "ALL") -> bool:
        return _feedback.submit_feedback(reg_number, student_name, message, dept, year)

    def delete_feedback(self, timestamp: str, reg_number: str) -> bool:
        return _feedback.delete_feedback(timestamp, reg_number)

    def delete_all_feedback(self, reg_number: str) -> bool:
        return _feedback.delete_all_feedback(reg_number)

    def update_feedback_status(self, timestamp: str, reg_number: str, new_status: str) -> bool:
        return _feedback.update_feedback_status(timestamp, reg_number, new_status)

    # ── REP REPLIES ─────────────────────────────────────────────
    def fetch_rep_replies(self, reg_number: str = "ALL", dept: str = "ALL", year: str = "ALL") -> List:
        return _rep_replies.fetch_rep_replies(reg_number, dept, year)

    def send_rep_reply(self, reg_number: str, message: str, rep_name: str = "Class Rep",
                       dept: str = "ALL", year: str = "ALL") -> bool:
        return _rep_replies.send_rep_reply(reg_number, message, rep_name, dept, year)

    def post_rep_reply(self, reg_number: str, student_name: str, message: str, rep_name: str = "Class Rep",
                       dept: str = "ALL", year: str = "ALL") -> bool:
        return _rep_replies.post_rep_reply(reg_number, student_name, message, rep_name, dept=dept, year=year)

    def mark_rep_reply_read(self, timestamp: str, reg_number: str) -> bool:
        return _rep_replies.mark_rep_reply_read(timestamp, reg_number)

    # ── REPS ────────────────────────────────────────────────────
    def fetch_reps(self) -> List:
        return _reps.fetch_reps()

    def verify_rep(self, dept: str, year: str, password: str) -> Dict:
        return _reps.verify_rep(dept, year, password)

    def assign_rep(self, dept: str, year: str, rep_name: str, rep_reg: str, password: str, email: str = "",
                   avatar_bytes: Optional[bytes] = None, avatar_mime: str = "image/jpeg") -> bool:
        return _reps.assign_rep(dept, year, rep_name, rep_reg, password, email, avatar_bytes, avatar_mime)

    def update_rep_email(self, dept: str, year: str, new_email: str) -> Dict:
        return _reps.update_rep_email(dept, year, new_email)

    def get_rep_email(self, dept: str, year: str):
        return _reps.get_rep_email(dept, year)

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

    # ── NOTIFICATIONS / BROADCAST ──────────────────
    def notify_student_whatsapp(self, reg_number: str, message: str) -> bool:
        return True

    def notify_class_whatsapp(self, dept: str, year: str, message: str) -> int:
        return 0

    def broadcast_whatsapp(self, dept: str, year: str, message: str) -> int:
        return 0

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

    # ── NOTIFICATIONS ───────────────────────────────────────────
    def fetch_notifications(self, reg_number: str, limit: int = 30) -> List:
        return _notifications.fetch_notifications(reg_number, limit)

    def unread_notification_count(self, reg_number: str) -> int:
        return _notifications.unread_notification_count(reg_number)

    def mark_notification_read(self, notification_id: str) -> bool:
        return _notifications.mark_notification_read(notification_id)

    def mark_all_notifications_read(self, reg_number: str) -> bool:
        return _notifications.mark_all_notifications_read(reg_number)


SheetDatabaseManager = SupabaseDatabaseManager
