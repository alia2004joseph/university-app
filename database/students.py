"""database/students.py — Student roster CRUD, PIN auth (replaces 'Roster' sheet)."""
import re
from typing import Dict, List, Optional
from .supabase_client import get_client, safe_call, hash_secret, verify_secret, none_if_all
from .avatars import upload_student_avatar, delete_student_avatar

ROSTER_COLUMNS = [
    "Timestamp", "Student Name", "Reg Number", "Course Code", "Contact",
    "Assigned Group", "Department", "Year", "Pin", "Email", "Avatar"
]

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def is_valid_email(email: str) -> bool:
    return bool(email) and bool(EMAIL_RE.match(email.strip()))


def _row_to_roster_dict(row: Dict) -> Dict:
    """Map a `students` table row to the legacy roster column names the
    UI (student.py / class_rep.py / Superadmin.py) already expects."""
    return {
        "Timestamp": row.get("created_at", ""),
        "Student Name": row.get("student_name", ""),
        "Reg Number": row.get("reg_number", ""),
        "Course Code": row.get("course_code", ""),
        "Contact": row.get("contact", ""),
        "Assigned Group": row.get("assigned_group", "Unassigned"),
        "Department": row.get("department_code", ""),
        "Year": row.get("year", ""),
        "Pin": "",  # never expose hashes to the UI
        "Email": row.get("email", ""),
        "Avatar": row.get("avatar_url", "") or "",
        "avatar_url": row.get("avatar_url", "") or "",
    }


def fetch_roster_rows(dept: str = "ALL", year: str = "ALL") -> List[Dict]:
    """Return roster rows shaped like the legacy sheet (list of dicts)."""
    def _run():
        q = get_client().table("students").select("*")
        d = none_if_all(dept)
        y = none_if_all(year)
        if d:
            q = q.eq("department_code", d)
        if y:
            q = q.eq("year", y)
        res = q.order("student_name").execute()
        return [_row_to_roster_dict(r) for r in (res.data or [])]

    return safe_call(_run, default=[], log_label="fetch_roster_rows")


def register_student(
    name: str, reg: str, code: str, contact: str, dept: str, year: str,
    pin: Optional[str] = None, email: str = "",
    avatar_bytes: Optional[bytes] = None, avatar_mime: str = "image/jpeg"
) -> Dict:
    parts = name.strip().split()
    if len(parts) >= 2:
        clean_name = f"{parts[0].upper()} {' '.join(p.title() for p in parts[1:])}"
    elif len(parts) == 1:
        clean_name = parts[0].upper()
    else:
        clean_name = "Unknown"

    email_clean = email.strip().lower()
    if not is_valid_email(email_clean):
        return {"status": "error", "message": "Please enter a valid email address (e.g. name@example.com)."}

    def _run():
        client = get_client()
        reg_u = reg.strip().upper()
        existing = client.table("students").select("id").eq("reg_number", reg_u).execute()
        if existing.data:
            return {"status": "error", "message": "A student with this registration number already exists."}

        existing_email = client.table("students").select("id").ilike("email", email_clean).execute()
        if existing_email.data:
            return {"status": "error", "message": "This email address is already registered to another account."}

        avatar_url = ""
        if avatar_bytes:
            avatar_url = upload_student_avatar(reg_u, avatar_bytes, avatar_mime) or ""

        client.table("students").insert({
            "student_name": clean_name,
            "reg_number": reg_u,
            "course_code": code.strip().upper() if code else "UNASSIGNED",
            "contact": contact.strip(),
            "assigned_group": "Unassigned",
            "department_code": dept.strip().upper(),
            "year": year.strip(),
            "pin_hash": hash_secret(pin.strip()) if pin else None,
            "email": email_clean,
            "avatar_url": avatar_url,
        }).execute()
        return {"status": "success"}

    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="register_student")


def delete_student(name: str) -> Dict:
    def _run():
        get_client().table("students").delete().eq("student_name", name.strip()).execute()
        return {"status": "success"}

    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="delete_student")


def save_group_allocations(allocations_dict: Dict) -> Dict:
    """allocations_dict: {student_name_or_reg: group_name, ...}
    Supports keys as Reg Number (e.g. 25/U/...) OR Student Name.
    """
    def _run():
        client = get_client()
        for key, group_name in allocations_dict.items():
            clean_key = str(key).strip()
            clean_group = str(group_name).strip()
            is_reg = any(c.isdigit() for c in clean_key) or ("/" in clean_key)
            if is_reg:
                client.table("students").update({"assigned_group": clean_group}).eq("reg_number", clean_key.upper()).execute()
            else:
                client.table("students").update({"assigned_group": clean_group}).eq("student_name", clean_key).execute()
        return {"status": "success"}

    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="save_group_allocations")

def assign_group(reg_number_or_name: str, group_name: str) -> bool:
    """Assign a single student (matched by reg number OR name) to a group."""
    def _run():
        client = get_client()
        key = reg_number_or_name.strip()
        match_col = "reg_number" if any(c.isdigit() for c in key) or "/" in key else "student_name"
        value = key.upper() if match_col == "reg_number" else key
        client.table("students").update({"assigned_group": group_name.strip()}) \
            .eq(match_col, value).execute()
        return True

    return bool(safe_call(_run, default=False, log_label="assign_group"))


def update_contact(reg_number: str, new_contact: str) -> bool:
    def _run():
        get_client().table("students").update({"contact": new_contact.strip()}) \
            .eq("reg_number", reg_number.strip().upper()).execute()
        return True

    return bool(safe_call(_run, default=False, log_label="update_contact"))


def update_whatsapp(reg_number: str, phone: str, apikey: str) -> bool:
    return True


    return bool(safe_call(_run, default=False, log_label="update_whatsapp"))


def update_email(reg_number: str, new_email: str) -> Dict:
    email_clean = new_email.strip().lower()
    if not is_valid_email(email_clean):
        return {"status": "error", "message": "Please enter a valid email address (e.g. name@example.com)."}

    def _run():
        client = get_client()
        reg_u = reg_number.strip().upper()
        existing = client.table("students").select("id").ilike("email", email_clean) \
            .neq("reg_number", reg_u).execute()
        if existing.data:
            return {"status": "error", "message": "This email address is already registered to another account."}

        client.table("students").update({"email": email_clean}).eq("reg_number", reg_u).execute()
        return {"status": "success"}

    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="update_email")


def update_student_avatar(reg_number: str, file_bytes: bytes, mime_type: str = "image/jpeg") -> Optional[str]:
    return upload_student_avatar(reg_number, file_bytes, mime_type)


def remove_student_avatar(reg_number: str) -> bool:
    return delete_student_avatar(reg_number)


def verify_student(reg_number: str, pin: str) -> Dict:
    def _run():
        client = get_client()
        reg_u = reg_number.strip().upper()
        res = client.table("students").select("*").eq("reg_number", reg_u).limit(1).execute()
        if not res.data:
            return {"status": "error", "message": "Registration number not found."}
        row = res.data[0]
        if not row.get("pin_hash"):
            return {"status": "error", "message": "No PIN set for this account. Use 'Forgot PIN' to set one."}
        if not verify_secret(pin.strip(), row["pin_hash"]):
            return {"status": "error", "message": "Incorrect PIN."}
        return {"status": "success", "student": _row_to_roster_dict(row)}

    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="verify_student")


def set_pin(reg_number: str, new_pin: str) -> bool:
    def _run():
        get_client().table("students").update({"pin_hash": hash_secret(new_pin.strip())}) \
            .eq("reg_number", reg_number.strip().upper()).execute()
        return True

    return bool(safe_call(_run, default=False, log_label="set_pin"))


def reset_pin(reg_number: str, contact: str, new_pin: str) -> Dict:
    def _run():
        client = get_client()
        reg_u = reg_number.strip().upper()
        res = client.table("students").select("id, contact").eq("reg_number", reg_u).limit(1).execute()
        if not res.data:
            return {"status": "error", "message": "Registration number not found."}
        if res.data[0].get("contact", "").strip() != contact.strip():
            return {"status": "error", "message": "Contact number does not match our records."}
        client.table("students").update({"pin_hash": hash_secret(new_pin.strip())}).eq("reg_number", reg_u).execute()
        return {"status": "success"}

    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="reset_pin")


def update_student_course_groups(student_reg: str, course_groups: Dict, dept: str = "", year: str = "") -> Dict:
    def _run():
        client = get_client()
        reg_u = student_reg.strip().upper()
        for course_unit, group_name in course_groups.items():
            client.table("course_unit_groups").upsert({
                "student_reg": reg_u,
                "department_code": dept or None,
                "year": year or None,
                "course_unit": course_unit,
                "group_name": group_name,
            }, on_conflict="student_reg,course_unit").execute()
        return {"status": "success"}

    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="update_student_course_groups")


def save_course_unit_groups(dept: str, year: str, course_groups: Dict) -> Dict:
    """course_groups: {student_name_or_reg: {course_unit: group_name, ...}, ...}"""
    def _run():
        client = get_client()
        for student_key, groups in course_groups.items():
            res = client.table("students").select("reg_number") \
                .or_(f"reg_number.eq.{student_key.upper()},student_name.eq.{student_key}").limit(1).execute()
            if not res.data:
                continue
            reg_u = res.data[0]["reg_number"]
            for course_unit, group_name in groups.items():
                client.table("course_unit_groups").upsert({
                    "student_reg": reg_u,
                    "department_code": dept or None,
                    "year": year or None,
                    "course_unit": course_unit,
                    "group_name": group_name,
                }, on_conflict="student_reg,course_unit").execute()
        return {"status": "success", "message": "Course unit groups saved"}

    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="save_course_unit_groups")


def fetch_course_unit_groups(student_name: str, dept: str = "ALL", year: str = "ALL") -> Dict:
    def _run():
        client = get_client()
        res = client.table("students").select("reg_number") \
            .or_(f"reg_number.eq.{student_name.upper()},student_name.eq.{student_name}").limit(1).execute()
        if not res.data:
            return {}
        reg_u = res.data[0]["reg_number"]
        groups_res = client.table("course_unit_groups").select("course_unit, group_name") \
            .eq("student_reg", reg_u).execute()
        return {g["course_unit"]: g["group_name"] for g in (groups_res.data or [])}

    return safe_call(_run, default={}, log_label="fetch_course_unit_groups")
