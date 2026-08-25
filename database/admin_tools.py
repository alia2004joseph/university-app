"""
database/admin_tools.py — Super Admin "developer" tools.

These replace the old Google-Sheets-specific meta-tools (arbitrary sheet
creation/renaming, the FunctionLibrary sheet used to store/run Apps
Script snippets, and the generic read/write-any-sheet explorer).

Design decision: Postgres tables are fixed by migration files (see
supabase/migrations/), not created/renamed/dropped at runtime by the
app. Doing schema DDL from an in-app "explorer" is both unnecessary now
that the schema is version-controlled SQL, and a real security risk
(arbitrary DDL triggered from the UI/AI chat). So:

  * list_sheets / read_sheet  -> work against the REAL known tables
  * create_sheet / rename_sheet / clear_sheet / delete_sheet
  * write_row / delete_row    -> return a friendly "not supported in
                                   Supabase mode" message instead of
                                   silently doing nothing or crashing
  * FunctionLibrary            -> becomes a real table for save/list;
                                   run/call return a friendly message
                                   since there is no more Apps Script
                                   runtime to execute against
"""

from typing import Dict, List, Union

from .supabase_client import get_client, safe_call

KNOWN_TABLES = [
    "departments", "students", "class_representatives", "announcements",
    "materials", "course_unit_groups", "feedback", "rep_replies",
    "timetable", "notifications", "notification_preferences",
    "chat_history", "ai_memory", "function_library", "app_config", "slots",
]

_NOT_SUPPORTED = {
    "status": "error",
    "message": (
        "Schema changes (create/rename/clear/delete table) aren't done from "
        "the app anymore — the database schema now lives in version-controlled "
        "SQL migrations under supabase/migrations/. Add a new migration file "
        "instead."
    ),
}


def list_sheets() -> List[Dict]:
    """
    Returns table info shaped like the old Sheet Manager expects:
    [{"name": ..., "rows": ..., "cols": ..., "protected": ...}, ...]
    "protected" marks core tables the app depends on (not deletable
    from the UI); row counts are fetched live from Supabase.
    """
    def _run():
        client = get_client()
        out = []
        for name in KNOWN_TABLES:
            try:
                res = client.table(name).select("*", count="exact").limit(1).execute()
                row_count = res.count or 0
                col_count = len(res.data[0]) if res.data else 0
            except Exception:
                row_count, col_count = 0, 0
            out.append({
                "name": name,
                "rows": row_count,
                "cols": col_count,
                "protected": True,  # every table here is a core, migration-managed table
            })
        return out
    return safe_call(_run, default=[], log_label="list_sheets")


def create_sheet(sheet_name: str, headers: List = None) -> Dict:
    return dict(_NOT_SUPPORTED)


def rename_sheet(old_name: str, new_name: str) -> Dict:
    return dict(_NOT_SUPPORTED)


def clear_sheet(sheet_name: str) -> Dict:
    def _run():
        if sheet_name not in KNOWN_TABLES:
            return {"status": "error", "message": f"Unknown table '{sheet_name}'."}
        get_client().table(sheet_name).delete().neq("id", "___none___").execute()
        return {"status": "success"}
    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="clear_sheet")


def delete_sheet(sheet_name: str) -> Dict:
    return dict(_NOT_SUPPORTED)


def read_sheet(sheet_name: str, filter_key: str = "", filter_value: str = "") -> Union[List, Dict]:
    def _run():
        if sheet_name not in KNOWN_TABLES:
            return {"status": "error", "message": f"Unknown table '{sheet_name}'."}
        client = get_client()
        q = client.table(sheet_name).select("*")
        if filter_key.strip() and filter_value.strip():
            q = q.eq(filter_key.strip(), filter_value.strip())
        res = q.execute()
        return res.data or []
    return safe_call(_run, default=[], log_label="read_sheet")


def write_row(sheet_name: str, row: List, add_timestamp: bool = True) -> Dict:
    return {
        "status": "error",
        "message": (
            "Writing a raw positional row isn't supported in Supabase mode "
            "(tables have typed, named columns). Use the dedicated function "
            f"for '{sheet_name}' instead (e.g. register_student, post_announcement)."
        ),
    }


def delete_row(sheet_name: str, match_key: str, match_value: str, delete_all: bool = False) -> Dict:
    def _run():
        if sheet_name not in KNOWN_TABLES:
            return {"status": "error", "message": f"Unknown table '{sheet_name}'."}
        client = get_client()
        q = client.table(sheet_name).delete().eq(match_key, match_value)
        q.execute()
        return {"status": "success"}
    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="delete_row")


# ─────────────────────────────────────────────────────────────
# FUNCTION LIBRARY
# ─────────────────────────────────────────────────────────────
def list_functions() -> List[Dict]:
    def _run():
        res = get_client().table("function_library").select("*").order("name").execute()
        return res.data or []
    return safe_call(_run, default=[], log_label="list_functions")


def save_function(name: str, script: str, description: str = "") -> Dict:
    def _run():
        get_client().table("function_library").upsert({
            "name": name.strip(), "script": script.strip(), "description": description.strip(),
        }, on_conflict="name").execute()
        return {"status": "success"}
    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="save_function")


def run_function(name: str, params: Dict = None) -> Dict:
    return {
        "status": "error",
        "message": (
            "Executing saved scripts isn't available in Supabase mode (there is "
            "no more Apps Script runtime). The script for "
            f"'{name}' is still stored for reference in the Function Library."
        ),
    }


def call_function(name: str, params: dict = None) -> dict:
    return run_function(name, params)