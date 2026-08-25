"""
database/supabase_client.py — Supabase connection + shared helpers.

Replaces the old Google Apps Script WEBHOOK_URL as the single source of
truth for how this app reaches its backend.

Credentials come from Streamlit secrets (`.streamlit/secrets.toml`) or
environment variables — never hardcoded here. See
`.streamlit/secrets.toml.example` for the expected keys.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets as pysecrets
from typing import Optional

import streamlit as st

try:
    from supabase import create_client, Client
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "The 'supabase' package is required. Install it with:\n"
        "    pip install supabase\n"
        "(see requirements.txt)"
    ) from e

log = logging.getLogger("database.supabase_client")

# "ALL" is this app's long-standing sentinel meaning "every department" /
# "every year". Supabase stores that as SQL NULL instead, so every service
# module converts between the two at the edges.
ALL = "ALL"


def _get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Read a secret from st.secrets first, then environment variables."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)


class SupabaseUnavailableError(RuntimeError):
    """Raised when Supabase credentials are missing or a connection can't
    be established. Callers should catch this (via `safe_call`) and show
    a friendly message instead of crashing the app."""


@st.cache_resource(show_spinner=False)
def get_client() -> "Client":
    """
    Return a cached Supabase client for the lifetime of the Streamlit
    server process. Uses the SERVICE ROLE key because this app's Python
    backend is the trusted party (the key never reaches the browser) —
    see supabase/migrations/003_storage_and_rls.sql for the reasoning.
    """
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_SERVICE_ROLE_KEY") or _get_secret("SUPABASE_ANON_KEY")

    if not url or not key:
        raise SupabaseUnavailableError(
            "Supabase is not configured yet. Add SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY to .streamlit/secrets.toml "
            "(see .streamlit/secrets.toml.example) and restart the app."
        )

    return create_client(url, key)


def is_configured() -> bool:
    """Cheap check used by the UI to show a setup banner instead of
    letting every page blow up with the same error."""
    try:
        get_client()
        return True
    except Exception:
        return False


def safe_call(fn, *args, default=None, log_label: str = "", **kwargs):
    """
    Run a Supabase operation and never let it crash the app.
    Returns `default` (and logs the real error) on any failure —
    satisfies the "Supabase failure must not crash the app" requirement.
    """
    try:
        return fn(*args, **kwargs)
    except SupabaseUnavailableError as e:
        log.warning("Supabase not configured (%s): %s", log_label, e)
        return default
    except Exception as e:
        log.error("Supabase error (%s): %s", log_label, e)
        return default


# ─────────────────────────────────────────────────────────────
# PASSWORD / PIN HASHING
# Lightweight, dependency-free PBKDF2 hashing so PINs/passwords are
# never stored in plaintext. Stored as "salt_hex$hash_hex".
# ─────────────────────────────────────────────────────────────
_PBKDF2_ITERATIONS = 200_000


def hash_secret(raw: str) -> str:
    salt = pysecrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_secret(raw: str, stored: str) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, hex_digest = stored.split("$", 1)
    try:
        digest = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS)
        return hmac.compare_digest(digest.hex(), hex_digest)
    except Exception:
        return False


def none_if_all(value: Optional[str]) -> Optional[str]:
    """Convert this app's "ALL" sentinel to SQL NULL for filtering/inserts."""
    if value is None:
        return None
    return None if value.strip().upper() == ALL else value


def all_if_none(value: Optional[str]) -> str:
    """Convert SQL NULL back to this app's "ALL" sentinel for display."""
    return value if value else ALL
