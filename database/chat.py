"""database/chat.py — AI Study Assistant chat history (replaces 'ChatHistory' sheet)."""

from typing import Dict, List

from .supabase_client import get_client, safe_call


def save_chat_message(reg_number: str, role: str, message: str) -> bool:
    def _run():
        get_client().table("chat_history").insert({
            "reg_number": reg_number.strip().upper(),
            "role": role,
            "message": message,
        }).execute()
        return True
    return bool(safe_call(_run, default=False, log_label="save_chat_message"))


def get_chat_history(reg_number: str, limit: int = 20) -> List[Dict]:
    def _run():
        res = get_client().table("chat_history").select("*") \
            .eq("reg_number", reg_number.strip().upper()) \
            .order("created_at", desc=True).limit(limit).execute()
        return list(reversed(res.data or []))
    return safe_call(_run, default=[], log_label="get_chat_history")


def clear_chat_history(reg_number: str) -> bool:
    def _run():
        get_client().table("chat_history").delete().eq("reg_number", reg_number.strip().upper()).execute()
        return True
    return bool(safe_call(_run, default=False, log_label="clear_chat_history"))
