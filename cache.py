"""
cache.py — Optimised, dept+year-aware data fetching layer.

Migrated from Google Sheets/Apps Script webhooks to Supabase. Function
names, signatures, TTLs and return shapes are unchanged so student.py,
class_rep.py and Superadmin.py don't need to change how they call these.
"""

import pandas as pd
import streamlit as st

from database import students as _students_svc
from database import announcements as _announcements_svc
from database import materials as _materials_svc
from database import feedback as _feedback_svc
from database import rep_replies as _rep_replies_svc
from database import reps as _reps_svc
from database import timetable as _timetable_svc
from database.materials import fetch_file_bytes as _fetch_file_bytes
from database.students import ROSTER_COLUMNS as EMPTY_COLUMNS  # noqa: F401  (kept for backward compat)

TTL_ROSTER        = 120   # 2 min
TTL_ANNOUNCEMENTS = 45    # 45 sec
TTL_MATERIALS     = 120   # 2 min
TTL_FEEDBACK      = 45    # 45 sec
TTL_FILE          = 3600  # 1 hour
TTL_REP_REPLIES   = 45    # 45 sec
TTL_REPS          = 60    # 1 min — rep accounts change infrequently
TTL_TIMETABLE     = 300   # 5 min — timetable rarely changes


def _normalize_roster_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Force columns that can have mixed types into a single consistent
    dtype, so PyArrow/Streamlit can render them without erroring."""
    string_cols = ["Pin", "Reg Number", "Contact", "Email"]
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
    return df


# ─────────────────────────────────────────────────────────────
# CACHED FETCHERS  (same names/signatures as before the migration)
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=TTL_ROSTER, show_spinner=False)
def cached_fetch_roster(dept: str = "ALL", year: str = "ALL") -> pd.DataFrame:
    rows = _students_svc.fetch_roster_rows(dept=dept, year=year)
    if not rows:
        return pd.DataFrame(columns=EMPTY_COLUMNS)
    df = pd.DataFrame(rows)
    return _normalize_roster_dtypes(df)


@st.cache_data(ttl=TTL_ANNOUNCEMENTS, show_spinner=False)
def cached_fetch_announcements(dept: str = "ALL", year: str = "ALL") -> list:
    return _announcements_svc.fetch_announcements(dept=dept, year=year)


@st.cache_data(ttl=TTL_MATERIALS, show_spinner=False)
def cached_fetch_materials(dept: str = "ALL", year: str = "ALL") -> list:
    return _materials_svc.fetch_materials(dept=dept, year=year)


@st.cache_data(ttl=TTL_FEEDBACK, show_spinner=False)
def cached_fetch_feedback(dept: str = "ALL", year: str = "ALL") -> list:
    return _feedback_svc.fetch_feedback(dept=dept, year=year)


@st.cache_data(ttl=TTL_FILE, show_spinner=False)
def cached_fetch_file(url: str) -> bytes:
    return _fetch_file_bytes(url)


@st.cache_data(ttl=TTL_REP_REPLIES, show_spinner=False)
def cached_fetch_rep_replies(reg_number: str = None, dept: str = "ALL", year: str = "ALL") -> list:
    return _rep_replies_svc.fetch_rep_replies(reg_number=reg_number, dept=dept, year=year)


@st.cache_data(ttl=TTL_TIMETABLE, show_spinner=False)
def cached_fetch_timetable(dept: str = "ALL", year: str = "ALL") -> list:
    return _timetable_svc.fetch_timetable(dept=dept, year=year)


@st.cache_data(ttl=TTL_REPS, show_spinner=False)
def cached_fetch_reps() -> list:
    return _reps_svc.fetch_reps()
