"""database/whatsapp.py — WhatsApp integration completely removed/disabled."""

def notify_student_whatsapp(reg_number: str, message: str) -> bool:
    return False

def broadcast_whatsapp(dept: str, year: str, message: str) -> int:
    return 0
