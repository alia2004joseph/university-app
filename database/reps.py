"""database/reps.py — Class Representative accounts (replaces 'Reps' sheet)."""
import re
from typing import Dict, List, Optional
from .supabase_client import get_client, safe_call, hash_secret, verify_secret
from .avatars import upload_rep_avatar, delete_rep_avatar

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def is_valid_email(email: str) -> bool:
    return bool(email) and bool(EMAIL_RE.match(email.strip()))


def fetch_reps() -> List[Dict]:
    def _run():
        res = get_client().table("class_representatives").select(
            "id, department_code, year, rep_name, rep_reg, email, avatar_url, created_at"
        ).execute()
        out = []
        for r in (res.data or []):
            out.append({
                "dept": r.get("department_code", ""),
                "year": r.get("year", ""),
                "rep_name": r.get("rep_name", ""),
                "rep_reg": r.get("rep_reg", ""),
                "email": r.get("email", "") or "",
                "avatar_url": r.get("avatar_url", "") or "",
                "Avatar": r.get("avatar_url", "") or "",
            })
        return out

    return safe_call(_run, default=[], log_label="fetch_reps")


def get_rep_email(dept: str, year: str) -> Optional[str]:
    def _run():
        res = get_client().table("class_representatives").select("email") \
            .eq("department_code", dept.strip().upper()).eq("year", year.strip()).limit(1).execute()
        if res.data and res.data[0].get("email"):
            return res.data[0]["email"]
        return None

    return safe_call(_run, default=None, log_label="get_rep_email")


def authenticate_rep(identifier: str, password: str) -> Dict:
    """
    Authenticate a Class Representative by credential (Reg Number, Email, or Full Name) + Password,
    without requiring them to manually select Department or Year.
    """
    id_clean = (identifier or "").strip()
    pw_clean = (password or "").strip()
    
    if not id_clean:
        return {"status": "error", "message": "Please enter your Representative ID, Registration Number, or Email."}
    if not pw_clean:
        return {"status": "error", "message": "Please enter your password."}
        
    def _run():
        client = get_client()
        # Fetch all class rep records to verify credentials
        res = client.table("class_representatives").select("*").execute()
        rows = res.data or []
        
        if not rows:
            return {"status": "error", "message": "No Class Representative accounts found in the database. Please contact the administrator."}
            
        id_lower = id_clean.lower()
        id_upper = id_clean.upper()
        
        # 1. Match on exact / case-insensitive reg number, email, or full name
        matched_rows = []
        for r in rows:
            r_reg = (r.get("rep_reg") or "").strip()
            r_email = (r.get("email") or "").strip()
            r_name = (r.get("rep_name") or "").strip()
            
            if (
                (r_reg and id_upper == r_reg.upper())
                or (r_email and id_lower == r_email.lower())
                or (r_name and id_lower == r_name.lower())
            ):
                matched_rows.append(r)
                
        # 2. Fallback partial match if exact didn't match (e.g. reg number partial)
        if not matched_rows:
            for r in rows:
                r_reg = (r.get("rep_reg") or "").strip().upper()
                r_email = (r.get("email") or "").strip().lower()
                if (r_reg and id_upper in r_reg) or (r_email and id_lower in r_email):
                    matched_rows.append(r)
                    
        # 3. If identifier wasn't found in candidates, but maybe the user entered something else or there's only 1 rep,
        # test all rows with the password as a safe fallback
        valid_rep = None
        if matched_rows:
            for cand in matched_rows:
                pw_hash = cand.get("password_hash") or ""
                if verify_secret(pw_clean, pw_hash):
                    valid_rep = cand
                    break
        else:
            # Check if any rep matches the password directly
            for cand in rows:
                pw_hash = cand.get("password_hash") or ""
                if verify_secret(pw_clean, pw_hash):
                    valid_rep = cand
                    break
                    
        if not valid_rep:
            if not matched_rows:
                return {"status": "error", "message": f"No representative account found matching '{id_clean}'. Please verify your ID or email."}
            return {"status": "error", "message": "Incorrect password for this representative account."}
            
        return {
            "status": "success",
            "dept": valid_rep.get("department_code", ""),
            "year": valid_rep.get("year", ""),
            "rep_name": valid_rep.get("rep_name", "Class Rep"),
            "rep_reg": valid_rep.get("rep_reg", ""),
            "avatar_url": valid_rep.get("avatar_url", "") or "",
            "email": valid_rep.get("email", "") or "",
        }
        
    return safe_call(_run, default={"status": "error", "message": "Database connection error. Please try again."}, log_label="authenticate_rep")


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
        return {
            "status": "success",
            "rep_name": row.get("rep_name", "Class Rep"),
            "rep_reg": row.get("rep_reg", ""),
            "avatar_url": row.get("avatar_url", "") or "",
            "email": row.get("email", "") or ""
        }

    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="verify_rep")


def assign_rep(
    dept: str, year: str, rep_name: str, rep_reg: str, password: str, email: str = "",
    avatar_bytes: Optional[bytes] = None, avatar_mime: str = "image/jpeg"
) -> bool:
    email_clean = (email or "").strip().lower()
    if email_clean and not is_valid_email(email_clean):
        return False

    def _run():
        avatar_url = ""
        if avatar_bytes:
            avatar_url = upload_rep_avatar(dept, year, avatar_bytes, avatar_mime) or ""

        data = {
            "department_code": dept.strip().upper(),
            "year": year.strip(),
            "rep_name": rep_name.strip(),
            "rep_reg": rep_reg.strip().upper(),
            "password_hash": hash_secret(password.strip()),
            "email": email_clean or None,
        }
        if avatar_url:
            data["avatar_url"] = avatar_url

        get_client().table("class_representatives").upsert(data, on_conflict="department_code,year").execute()
        return True

    return bool(safe_call(_run, default=False, log_label="assign_rep"))


def update_rep_avatar(dept: str, year: str, file_bytes: bytes, mime_type: str = "image/jpeg") -> Optional[str]:
    return upload_rep_avatar(dept, year, file_bytes, mime_type)


def remove_rep_avatar(dept: str, year: str) -> bool:
    return delete_rep_avatar(dept, year)


def update_rep_email(dept: str, year: str, new_email: str) -> Dict:
    email_clean = new_email.strip().lower()
    if not is_valid_email(email_clean):
        return {"status": "error", "message": "Please enter a valid email address (e.g. name@example.com)."}

    def _run():
        get_client().table("class_representatives").update({"email": email_clean}) \
            .eq("department_code", dept.strip().upper()).eq("year", year.strip()).execute()
        return {"status": "success"}

    return safe_call(_run, default={"status": "error", "message": "Database unavailable"}, log_label="update_rep_email")


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
