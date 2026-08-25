"""
supabase/seed_demo_data.py — Optional: populate a small demo dataset.

Run this AFTER applying the migrations, if you want some starter data
to click around with (departments, a couple of students, a class rep,
one announcement) instead of starting from a totally empty database.

Usage:
    export SUPABASE_URL=...
    export SUPABASE_SERVICE_ROLE_KEY=...
    python supabase/seed_demo_data.py

Reset (wipe demo data) — run with --reset:
    python supabase/seed_demo_data.py --reset

This mirrors the app's own password hashing (PBKDF2) so demo accounts
can log in through the normal login forms.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root

from supabase import create_client
from database.supabase_client import hash_secret

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

DEMO_TABLES = [
    "notifications", "rep_replies", "feedback", "course_unit_groups",
    "materials", "announcements", "timetable", "class_representatives", "students",
]


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables first.")
        sys.exit(1)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    if "--reset" in sys.argv:
        print("Wiping demo data...")
        for t in DEMO_TABLES:
            client.table(t).delete().neq("id", "___none___" if t != "students" else "").execute()
        print("Done. (Departments were kept — delete manually if you want a fully blank schema.)")
        return

    print("Seeding departments...")
    client.table("departments").upsert([
        {"code": "MEC", "name": "Mechanical Engineering", "color": "#1a56db",
         "light": "#dbeafe", "courses": ["BMEC", "BBPE"]},
        {"code": "ELE", "name": "Electrical Engineering", "color": "#16a34a",
         "light": "#dcfce7", "courses": ["BELE", "BTEL"]},
    ], on_conflict="code").execute()

    print("Seeding a class representative (MEC / Year 1, password: demo1234)...")
    client.table("class_representatives").upsert({
        "department_code": "MEC", "year": "Year 1",
        "rep_name": "Demo Class Rep", "rep_reg": "MEC/001/2024",
        "password_hash": hash_secret("demo1234"),
    }, on_conflict="department_code,year").execute()

    print("Seeding two demo students (PIN: 1234)...")
    client.table("students").upsert([
        {"reg_number": "MEC/002/2024", "student_name": "ALICE Nakato", "course_code": "BMEC",
         "contact": "0700000001", "department_code": "MEC", "year": "Year 1",
         "pin_hash": hash_secret("1234")},
        {"reg_number": "MEC/003/2024", "student_name": "BRIAN Okello", "course_code": "BMEC",
         "contact": "0700000002", "department_code": "MEC", "year": "Year 1",
         "pin_hash": hash_secret("1234")},
    ], on_conflict="reg_number").execute()

    print("Done. Demo accounts:")
    print("  Class Rep login → Dept: MEC, Year: Year 1, Password: demo1234")
    print("  Student login   → Reg: MEC/002/2024, PIN: 1234")
    print("  Student login   → Reg: MEC/003/2024, PIN: 1234")


if __name__ == "__main__":
    main()
