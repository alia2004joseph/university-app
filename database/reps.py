"""database/reps.py — Class Representative accounts (replaces 'Reps' sheet)."""

from typing import Dict, List

from .supabase_client import get_client, safe_call, hash_secret, verify_secret


def fetch_reps() -> List[Dict]:
    def _run():
        res = get_client().table("class_representatives").select(
            "id, department_code, year, rep_name, rep_reg, created_at"
        ).execute()
        out = []
        for r in (res.data or []):
            out.append({
                "dept": r.get("department_code", ""),
                "year": r.get("year", ""),
                "rep_name": r.get("rep_name", ""),
                "rep_reg": r.get("rep_reg", ""),
            })
        return out
    return safe_call(_run, default=[], log_label="fetch_reps")


def verify_rep(dept: str, year: str, password: str) -> Dict:
    def _run():
        client = get_client()
        res = client.table("class_representatives").select("*") \
            .eq("department_code", dept.strip().upper()).eq("year", year.strip()).limit(1).execute()
        if not res.data:
            return {"status": "error", "message": "No Class Rep is assigned for this department/year."}
        row = res.data[0]
        if not verify_secret(password.strip(), row["password_hash"]):
            return {"status": "error", "message": "Incorrect password."}
        return {"status": "success", "rep_name": row.get("rep_name", "Class Rep"), "rep_reg": row.get("rep_reg", "")}
    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="verify_rep")


def assign_rep(dept: str, year: str, rep_name: str, rep_reg: str, password: str) -> bool:
    def _run():
        get_client().table("class_representatives").upsert({
            "department_code": dept.strip().upper(),
            "year": year.strip(),
            "rep_name": rep_name.strip(),
            "rep_reg": rep_reg.strip().upper(),
            "password_hash": hash_secret(password.strip()),
        }, on_conflict="department_code,year").execute()
        return True
    return bool(safe_call(_run, default=False, log_label="assign_rep"))


def delete_rep(dept: str, year: str) -> bool:
    def _run():
        get_client().table("class_representatives").delete() \
            .eq("department_code", dept.strip().upper()).eq("year", year.strip()).execute()
        return True
    return bool(safe_call(_run, default=False, log_label="delete_rep"))


def change_rep_password(dept: str, year: str, old_password: str, new_password: str) -> Dict:
    def _run():
        client = get_client()
        res = client.table("class_representatives").select("password_hash") \
            .eq("department_code", dept.strip().upper()).eq("year", year.strip()).limit(1).execute()
        if not res.data:
            return {"status": "error", "message": "Class Rep account not found."}
        if not verify_secret(old_password.strip(), res.data[0]["password_hash"]):
            return {"status": "error", "message": "Old password is incorrect."}
        client.table("class_representatives").update({"password_hash": hash_secret(new_password.strip())}) \
            .eq("department_code", dept.strip().upper()).eq("year", year.strip()).execute()
        return {"status": "success"}
    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="change_rep_password")
