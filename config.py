"""
config.py — Dynamic department configuration.
Departments are loaded from Supabase at runtime.
Falls back to hardcoded defaults if Supabase is unavailable/unconfigured.
"""
import streamlit as st

from database.departments import fetch_departments as _fetch_departments_from_db

YEARS = ["Year 1", "Year 2", "Year 3", "Year 4"]

# Preset colour palette for admin to pick from
COLOUR_PALETTE = [
    {"name": "Navy Blue",  "hex": "#1e40af", "light": "#eff6ff"},
    {"name": "Emerald",    "hex": "#059669", "light": "#ecfdf5"},
    {"name": "Amber",      "hex": "#d97706", "light": "#fffbeb"},
    {"name": "Indigo",     "hex": "#4338ca", "light": "#e0e7ff"},
    {"name": "Teal",       "hex": "#0f766e", "light": "#f0fdfa"},
    {"name": "Slate",      "hex": "#334155", "light": "#f1f5f9"},
    {"name": "Ruby",       "hex": "#be123c", "light": "#ffe4e6"},
    {"name": "Cobalt",     "hex": "#2563eb", "light": "#eff6ff"},
]

# Hardcoded fallback — used if Supabase is unavailable/not yet configured,
# so the app is still usable (with demo departments) before you finish
# setup. See README_SUPABASE_MIGRATION.md.
FALLBACK_DEPARTMENTS = {
    "MEC": {"name": "Mechanical Engineering", "color": "#1e40af",
            "light": "#eff6ff", "courses": ["BMEC","BBPE","BWIE","BAGE"]},
    "ELE": {"name": "Electrical Engineering",  "color": "#059669",
            "light": "#ecfdf5", "courses": ["BELE","BTEL","BPOW"]},
    "CIV": {"name": "Civil Engineering",       "color": "#d97706",
            "light": "#fffbeb", "courses": ["BCIV","BSTR","BENV"]},
    "OTH": {"name": "Others",                  "color": "#334155",
            "light": "#f1f5f9", "courses": ["OTHER"]},
}


@st.cache_data(ttl=120, show_spinner=False)
def load_departments() -> dict:
    """
    Load departments from Supabase.
    Falls back to FALLBACK_DEPARTMENTS if unavailable/empty.
    """
    try:
        rows = _fetch_departments_from_db()
        if rows:
            depts = {}
            for row in rows:
                code = str(row.get("code", "")).strip().upper()
                if not code:
                    continue
                courses = row.get("courses") or []
                if isinstance(courses, str):
                    courses = [c.strip().upper() for c in courses.split(",") if c.strip()]
                depts[code] = {
                    "name":    str(row.get("name", code)).strip(),
                    "color":   str(row.get("color", "#1a56db")).strip(),
                    "light":   str(row.get("light", "#dbeafe")).strip(),
                    "courses": courses if courses else ["OTHER"],
                }
            if depts:
                return depts
    except Exception as e:
        print(f"[config] Departments fetch error: {e}")
    return FALLBACK_DEPARTMENTS


def get_departments() -> dict:
    return load_departments()

def get_dept_codes() -> list:
    return list(load_departments().keys())

def dept_color(code: str) -> str:
    return load_departments().get(code, FALLBACK_DEPARTMENTS.get("OTH", {})).get("color", "#1a56db")

def dept_light(code: str) -> str:
    return load_departments().get(code, FALLBACK_DEPARTMENTS.get("OTH", {})).get("light", "#dbeafe")

def dept_name(code: str) -> str:
    return load_departments().get(code, FALLBACK_DEPARTMENTS.get("OTH", {})).get("name", code)

def dept_courses(code: str) -> list:
    return load_departments().get(code, FALLBACK_DEPARTMENTS.get("OTH", {})).get("courses", ["OTHER"])

def get_all_courses() -> list:
    return [c for v in load_departments().values() for c in v.get("courses", [])]
