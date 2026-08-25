"""database/slots.py — Configurable AI/quick-action 'slot' system
(replaces the 'Slots' sheet)."""

import uuid
from typing import Dict, List

from .supabase_client import get_client, safe_call


def _row_to_slot(row: Dict) -> Dict:
    out = dict(row.get("slot_data") or {})
    out.update({
        "slotid": row.get("id"),
        "audience": row.get("audience"),
        "dept": row.get("department_code"),
        "year": row.get("year"),
        "active": row.get("active"),
    })
    return out


def get_active_slots(dept: str, year: str, audience: str = "student") -> List[Dict]:
    def _run():
        client = get_client()
        res = client.table("slots").select("*").eq("audience", audience).eq("active", True).execute()
        rows = res.data or []
        out = []
        for r in rows:
            r_dept, r_year = r.get("department_code", "ALL"), r.get("year", "ALL")
            if r_dept in ("ALL", dept.strip().upper()) and r_year in ("ALL", year.strip()):
                out.append(_row_to_slot(r))
        return out
    return safe_call(_run, default=[], log_label="get_active_slots")


def get_all_slots(audience: str = "student") -> List[Dict]:
    def _run():
        res = get_client().table("slots").select("*").eq("audience", audience).execute()
        return [_row_to_slot(r) for r in (res.data or [])]
    return safe_call(_run, default=[], log_label="get_all_slots")


def save_slot(slot_data: Dict, audience: str = "student") -> Dict:
    def _run():
        client = get_client()
        slot_id = slot_data.get("slotid") or slot_data.get("id") or str(uuid.uuid4())
        payload = {k: v for k, v in slot_data.items() if k not in ("slotid", "id", "dept", "year", "active")}
        client.table("slots").upsert({
            "id": slot_id,
            "audience": audience,
            "department_code": slot_data.get("dept", "ALL"),
            "year": slot_data.get("year", "ALL"),
            "active": slot_data.get("active", True),
            "slot_data": payload,
        }, on_conflict="id").execute()
        return {"status": "success", "slotid": slot_id}
    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="save_slot")


def delete_slot(slot_id: str, audience: str = "student") -> Dict:
    def _run():
        get_client().table("slots").delete().eq("id", slot_id).execute()
        return {"status": "success"}
    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="delete_slot")


def toggle_slot(slot_id: str, active: bool, audience: str = "student") -> Dict:
    def _run():
        get_client().table("slots").update({"active": active}).eq("id", slot_id).execute()
        return {"status": "success"}
    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="toggle_slot")
