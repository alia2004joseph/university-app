"""
database/avatars.py — Profile photo storage and retrieval for Students, Reps, and Admins.
Supports Supabase Storage bucket ('avatars') with graceful Base64 data-URI fallback.
"""
from __future__ import annotations
import base64
import io
import re
import time
from typing import Optional
from .supabase_client import get_client, safe_call

AVATARS_BUCKET = "avatars"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def _sanitize_id(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]", "_", str(raw).strip().upper())


def optimize_image_bytes(file_bytes: bytes, max_size: int = 400) -> tuple[bytes, str]:
    """
    Downscale and compress profile image to max_size x max_size JPEG to save bandwidth.
    Falls back to raw bytes if PIL is not installed.
    """
    try:
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(file_bytes))
        img = ImageOps.exif_transpose(img)  # Handle smartphone orientation
        
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        out_buf = io.BytesIO()
        img.save(out_buf, format="JPEG", quality=85, optimize=True)
        return out_buf.getvalue(), "image/jpeg"
    except Exception:
        # Fallback to original bytes
        return file_bytes, "image/jpeg"


def _bytes_to_data_uri(file_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def _upload_to_storage_or_data_uri(storage_path: str, file_bytes: bytes, mime_type: str) -> str:
    """
    Attempt to upload to Supabase storage bucket 'avatars'.
    If storage bucket is unavailable or errors, return an optimized base64 data-URI.
    """
    opt_bytes, opt_mime = optimize_image_bytes(file_bytes)
    
    def _run_storage():
        client = get_client()
        # Upload or overwrite in bucket
        try:
            client.storage.from_(AVATARS_BUCKET).upload(
                storage_path,
                opt_bytes,
                {"content-type": opt_mime, "upsert": "true"}
            )
            return client.storage.from_(AVATARS_BUCKET).get_public_url(storage_path)
        except Exception:
            return None

    public_url = safe_call(_run_storage, default=None, log_label=f"avatar_storage_{storage_path}")
    if public_url:
        return public_url
    
    # Fallback to embedded data URI
    return _bytes_to_data_uri(opt_bytes, opt_mime)


# ─────────────────────────────────────────────────────────────
# STUDENT AVATARS
# ─────────────────────────────────────────────────────────────

def upload_student_avatar(reg_number: str, file_bytes: bytes, mime_type: str = "image/jpeg") -> Optional[str]:
    clean_reg = _sanitize_id(reg_number)
    path = f"students/{clean_reg}.jpg"
    avatar_url = _upload_to_storage_or_data_uri(path, file_bytes, mime_type)
    
    def _run_db():
        get_client().table("students").update({"avatar_url": avatar_url}) \
            .eq("reg_number", reg_number.strip().upper()).execute()
        return avatar_url

    res = safe_call(_run_db, default=avatar_url, log_label="upload_student_avatar")
    return res or avatar_url


def delete_student_avatar(reg_number: str) -> bool:
    clean_reg = _sanitize_id(reg_number)
    path = f"students/{clean_reg}.jpg"
    
    def _run():
        client = get_client()
        try:
            client.storage.from_(AVATARS_BUCKET).remove([path])
        except Exception:
            pass
        client.table("students").update({"avatar_url": ""}) \
            .eq("reg_number", reg_number.strip().upper()).execute()
        return True

    return bool(safe_call(_run, default=True, log_label="delete_student_avatar"))


# ─────────────────────────────────────────────────────────────
# CLASS REP AVATARS
# ─────────────────────────────────────────────────────────────

def upload_rep_avatar(dept: str, year: str, file_bytes: bytes, mime_type: str = "image/jpeg") -> Optional[str]:
    clean_key = f"{_sanitize_id(dept)}_{_sanitize_id(year)}"
    path = f"reps/{clean_key}.jpg"
    avatar_url = _upload_to_storage_or_data_uri(path, file_bytes, mime_type)
    
    def _run_db():
        get_client().table("class_representatives").update({"avatar_url": avatar_url}) \
            .eq("department_code", dept.strip().upper()).eq("year", year.strip()).execute()
        return avatar_url

    res = safe_call(_run_db, default=avatar_url, log_label="upload_rep_avatar")
    return res or avatar_url


def delete_rep_avatar(dept: str, year: str) -> bool:
    clean_key = f"{_sanitize_id(dept)}_{_sanitize_id(year)}"
    path = f"reps/{clean_key}.jpg"
    
    def _run():
        client = get_client()
        try:
            client.storage.from_(AVATARS_BUCKET).remove([path])
        except Exception:
            pass
        client.table("class_representatives").update({"avatar_url": ""}) \
            .eq("department_code", dept.strip().upper()).eq("year", year.strip()).execute()
        return True

    return bool(safe_call(_run, default=True, log_label="delete_rep_avatar"))


# ─────────────────────────────────────────────────────────────
# SUPER ADMIN AVATARS
# ─────────────────────────────────────────────────────────────

def upload_admin_avatar(file_bytes: bytes, mime_type: str = "image/jpeg", admin_id: str = "superadmin") -> Optional[str]:
    path = f"admins/{_sanitize_id(admin_id)}.jpg"
    avatar_url = _upload_to_storage_or_data_uri(path, file_bytes, mime_type)
    
    def _run_db():
        from .config_store import set_config
        set_config("admin_avatar_url", avatar_url, description="Super Admin profile photo URL")
        return avatar_url

    return safe_call(_run_db, default=avatar_url, log_label="upload_admin_avatar") or avatar_url


def get_admin_avatar(admin_id: str = "superadmin") -> str:
    def _run_db():
        from .config_store import get_config_value
        return get_config_value("admin_avatar_url") or ""

    return safe_call(_run_db, default="", log_label="get_admin_avatar") or ""


def delete_admin_avatar(admin_id: str = "superadmin") -> bool:
    path = f"admins/{_sanitize_id(admin_id)}.jpg"
    
    def _run():
        client = get_client()
        try:
            client.storage.from_(AVATARS_BUCKET).remove([path])
        except Exception:
            pass
        from .config_store import set_config
        set_config("admin_avatar_url", "", description="Super Admin profile photo URL")
        return True

    return bool(safe_call(_run, default=True, log_label="delete_admin_avatar"))


# ─────────────────────────────────────────────────────────────
# HTML AVATAR RENDER HELPER
# ─────────────────────────────────────────────────────────────

def render_avatar_html(
    avatar_url: Optional[str],
    name: str,
    size: int = 42,
    color: str = "#1a56db",
    light: str = "#dbeafe",
    extra_css: str = "",
    border: bool = True
) -> str:
    """
    Returns an HTML string rendering an image avatar if url exists,
    or a stylized colored initial circle if not.
    """
    initial = (name.strip()[0].upper() if name and name.strip() else "?")
    border_style = f"border: 2px solid {color};" if border else ""
    
    if avatar_url and str(avatar_url).strip() and str(avatar_url).strip() != "#":
        return f"""<img src="{avatar_url.strip()}" alt="{name}" style="width:{size}px;height:{size}px;border-radius:50%;object-fit:cover;flex-shrink:0;{border_style}{extra_css}" />"""
    
    font_size = max(10, int(size * 0.45))
    return f"""<div style="width:{size}px;height:{size}px;border-radius:50%;background:{light};color:{color};display:flex;align-items:center;justify-content:center;font-size:{font_size}px;font-weight:800;flex-shrink:0;{border_style}{extra_css}">{initial}</div>"""
