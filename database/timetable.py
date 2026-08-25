"""database/timetable.py — Class timetable (replaces 'Timetable' sheet)."""

from typing import Dict, List

from .supabase_client import get_client, safe_call
from .notifications import _students_in_scope


def fetch_timetable(dept: str = "ALL", year: str = "ALL") -> List[Dict]:
    def _run():
        client = get_client()
        q = client.table("timetable").select("*")
        if dept != "ALL":
            q = q.eq("department_code", dept.strip().upper())
        if year != "ALL":
            q = q.eq("year", year.strip())
        res = q.execute()
        return res.data or []
    return safe_call(_run, default=[], log_label="fetch_timetable")


def add_timetable_entry(dept: str, year: str, day: str, time: str, course: str,
                         lecturer: str = "", color: str = "", entry_type: str = "Weekly",
                         notify: bool = False) -> bool:
    def _run():
        client = get_client()
        client.table("timetable").upsert({
            "department_code": dept.strip().upper(),
            "year": year.strip(),
            "day": day.strip(),
            "time": time.strip(),
            "course": course.strip().upper(),
            "lecturer": lecturer.strip(),
            "color": color.strip(),
            "entry_type": entry_type.strip(),
        }, on_conflict="department_code,year,day,time").execute()

        if notify:
            from .notifications import notify_student
            for reg in _students_in_scope(dept, year):
                notify_student(
                    reg, "Timetable Updated",
                    f"{course.strip().upper()} on {day.strip()} at {time.strip()}.",
                    notification_type="timetable",
                )
        return True
    return bool(safe_call(_run, default=False, log_label="add_timetable_entry"))


def delete_timetable_entry(dept: str, year: str, day: str, time: str) -> bool:
    def _run():
        get_client().table("timetable").delete() \
            .eq("department_code", dept.strip().upper()).eq("year", year.strip()) \
            .eq("day", day.strip()).eq("time", time.strip()).execute()
        return True
    return bool(safe_call(_run, default=False, log_label="delete_timetable_entry"))


def clear_timetable(dept: str, year: str) -> bool:
    def _run():
        get_client().table("timetable").delete() \
            .eq("department_code", dept.strip().upper()).eq("year", year.strip()).execute()
        return True
    return bool(safe_call(_run, default=False, log_label="clear_timetable"))
