"""database/materials.py — Learning materials (files in Supabase Storage,
metadata in Postgres). Replaces the old Drive-upload + 'Materials' sheet."""

import re
import time
import uuid
from typing import Dict, List

import requests

from .supabase_client import get_client, safe_call, none_if_all
from .notifications import notify_students_for_material

BUCKET = "materials"


def _safe_filename(name: str) -> str:
    name = name.strip().replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9_.\-]", "", name) or "file"


def _public_url(file_path: str) -> str:
    return get_client().storage.from_(BUCKET).get_public_url(file_path)


def _row_to_material_dict(row: Dict) -> Dict:
    return {
        "name": row.get("title", "Unnamed"),
        "url": _public_url(row["file_path"]) if row.get("file_path") else "#",
        "dept": row.get("department_code") or "ALL",
        "year": row.get("year") or "ALL",
        "id": row.get("id", ""),
    }


def fetch_materials(dept: str = "ALL", year: str = "ALL") -> List[Dict]:
    def _run():
        client = get_client()
        q = client.table("materials").select("*")
        d, y = none_if_all(dept), none_if_all(year)
        if d:
            q = q.or_(f"department_code.eq.{d},department_code.is.null")
        if y:
            q = q.or_(f"year.eq.{y},year.is.null")
        res = q.order("created_at", desc=True).execute()
        return [_row_to_material_dict(r) for r in (res.data or [])]
    return safe_call(_run, default=[], log_label="fetch_materials")


def fetch_file_bytes(url: str) -> bytes:
    """Download material bytes. Materials are stored in a public Storage
    bucket, so a plain HTTPS GET (same contract as the old Drive links)
    works unchanged for callers."""
    try:
        r = requests.get(url, timeout=30)
        return r.content if r.status_code == 200 else b""
    except Exception as e:
        print(f"[materials] file fetch error: {e}")
        return b""


def upload_material(
    file_bytes, file_name: str, mime_type: str,
    dept: str = "ALL", year: str = "ALL", notify_whatsapp: bool = False,
    title: str = "", uploaded_by: str = "Class Rep",
) -> bool:
    def _run():
        client = get_client()
        unique_prefix = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
        storage_path = f"{dept}/{year}/{unique_prefix}_{_safe_filename(file_name)}"

        client.storage.from_(BUCKET).upload(
            storage_path, file_bytes,
            {"content-type": mime_type or "application/octet-stream"},
        )

        row = client.table("materials").insert({
            "title": title or file_name,
            "file_path": storage_path,
            "mime_type": mime_type or "application/octet-stream",
            "department_code": none_if_all(dept),
            "year": none_if_all(year),
            "uploaded_by": uploaded_by,
            "notify_whatsapp": notify_whatsapp,
        }).execute()

        if row.data:
            notify_students_for_material(row.data[0], dept=dept, year=year)
        return True
    return bool(safe_call(_run, default=False, log_label="upload_material"))


def delete_material(file_name: str) -> bool:
    def _run():
        client = get_client()
        res = client.table("materials").select("id, file_path").eq("title", file_name.strip()).execute()
        for row in (res.data or []):
            if row.get("file_path"):
                try:
                    client.storage.from_(BUCKET).remove([row["file_path"]])
                except Exception as e:
                    print(f"[materials] storage delete error: {e}")
            client.table("materials").delete().eq("id", row["id"]).execute()
        return True
    return bool(safe_call(_run, default=False, log_label="delete_material"))
