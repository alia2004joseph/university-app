"""database/ai_memory.py — Master Super Admin AI persistent memory
(replaces 'MasterAIMemory' sheet)."""

from typing import List, Optional

from .supabase_client import get_client, safe_call


def save_master_ai_memory(mem_type: str, key: str, value: str) -> bool:
    def _run():
        get_client().table("ai_memory").upsert({
            "mem_type": mem_type, "key": key, "value": value,
        }, on_conflict="mem_type,key").execute()
        return True
    return bool(safe_call(_run, default=False, log_label="save_master_ai_memory"))


def load_master_ai_memory(mem_type: Optional[str] = None) -> list:
    def _run():
        client = get_client()
        q = client.table("ai_memory").select("*")
        if mem_type:
            q = q.eq("mem_type", mem_type)
        res = q.order("updated_at", desc=True).execute()
        return res.data or []
    return safe_call(_run, default=[], log_label="load_master_ai_memory")


def delete_master_ai_memory(mem_type: str, key: str) -> bool:
    def _run():
        get_client().table("ai_memory").delete().eq("mem_type", mem_type).eq("key", key).execute()
        return True
    return bool(safe_call(_run, default=False, log_label="delete_master_ai_memory"))


def clear_master_ai_memory(mem_type: str) -> bool:
    def _run():
        get_client().table("ai_memory").delete().eq("mem_type", mem_type).execute()
        return True
    return bool(safe_call(_run, default=False, log_label="clear_master_ai_memory"))
