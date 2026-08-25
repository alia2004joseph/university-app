"""database/departments.py — Department CRUD (replaces the 'Departments' sheet)."""

from typing import Dict, List

from .supabase_client import get_client, safe_call


def fetch_departments() -> List[Dict]:
    def _run():
        res = get_client().table("departments").select("*").order("code").execute()
        return res.data or []
    return safe_call(_run, default=[], log_label="fetch_departments")


def add_department(code: str, name: str, color: str, light: str, courses: str) -> bool:
    def _run():
        course_list = [c.strip().upper() for c in courses.split(",") if c.strip()]
        get_client().table("departments").insert({
            "code": code.strip().upper(),
            "name": name.strip(),
            "color": color.strip(),
            "light": light.strip(),
            "courses": course_list,
        }).execute()
        return True
    return bool(safe_call(_run, default=False, log_label="add_department"))


def update_department(code: str, name: str, color: str, light: str, courses: str) -> bool:
    def _run():
        course_list = [c.strip().upper() for c in courses.split(",") if c.strip()]
        get_client().table("departments").update({
            "name": name.strip(),
            "color": color.strip(),
            "light": light.strip(),
            "courses": course_list,
        }).eq("code", code.strip().upper()).execute()
        return True
    return bool(safe_call(_run, default=False, log_label="update_department"))


def delete_department(code: str) -> Dict:
    def _run():
        client = get_client()
        code_u = code.strip().upper()
        in_use = client.table("students").select("id", count="exact") \
            .eq("department_code", code_u).limit(1).execute()
        if (in_use.count or 0) > 0:
            return {"status": "error", "message": "Cannot delete: students are registered in this department."}
        client.table("departments").delete().eq("code", code_u).execute()
        return {"status": "success"}
    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="delete_department")
