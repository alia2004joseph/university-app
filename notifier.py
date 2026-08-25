"""
notifier.py — Smart University WhatsApp Notification Brain
═══════════════════════════════════════════════════════════
Architecture:
    Supabase (Timetable + Students tables)
        ↓
    Python Logic (this file — reads, decides, targets)
        ↓
    APScheduler (auto triggers at 6:30 AM, 30min & 15min before lectures)
        ↓
    CallMeBot API
        ↓
    WhatsApp messages → students

Run this script on a server (Railway, Render, or any VPS).
It runs 24/7 independently of the Streamlit app, so it reads Supabase
credentials from environment variables / a .env file rather than
st.secrets (which only exists inside a running Streamlit process).

Setup:
    pip install requests apscheduler pytz supabase python-dotenv
    export SUPABASE_URL=...            # or put these in a .env file
    export SUPABASE_SERVICE_ROLE_KEY=...
    python notifier.py
"""

import os
import requests
import logging
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars can be set directly instead

from supabase import create_client

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_ANON_KEY", "")

TIMEZONE        = "Africa/Kampala"   # Uganda timezone (UTC+3)
MORNING_HOUR    = 6                  # Morning reminder fires at 6:30 AM
MORNING_MINUTE  = 30
PRE_LECTURE_30  = 30                 # Minutes before lecture for first reminder
PRE_LECTURE_15  = 15                 # Minutes before lecture for second reminder
REQUEST_TIMEOUT = 15                 # Seconds for webhook requests
CALLMEBOT_DELAY = 0.4               # Seconds between WhatsApp sends (rate limit)

# Days mapping — GAS timetable stores full day names
DAY_MAP = {
    "Monday":    0,
    "Tuesday":   1,
    "Wednesday": 2,
    "Thursday":  3,
    "Friday":    4,
    "Saturday":  5,
    "Sunday":    6,
}

# ─────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("notifier")

# ─────────────────────────────────────────────────────────────
# PERSISTENT HTTP SESSION (still used for CallMeBot WhatsApp sends)
# ─────────────────────────────────────────────────────────────
_session = requests.Session()
_session.headers.update({"Content-Type": "application/json"})

# ─────────────────────────────────────────────────────────────
# SUPABASE CLIENT (standalone — no Streamlit context here)
# ─────────────────────────────────────────────────────────────
_supabase_client = None


def get_supabase():
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not set. "
                "Export them as environment variables or put them in a .env file "
                "next to notifier.py before running this script."
            )
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


# ═════════════════════════════════════════════════════════════
# ██  DATA LAYER — fetch from Supabase (no Streamlit cache)
# ═════════════════════════════════════════════════════════════

def fetch_timetable(dept: str = "ALL", year: str = "ALL") -> list:
    """Fetch all timetable entries from Supabase, scoped by dept+year."""
    try:
        client = get_supabase()
        q = client.table("timetable").select("*")
        if dept != "ALL": q = q.eq("department_code", dept)
        if year != "ALL": q = q.eq("year", year)
        res = q.execute()
        data = res.data or []
        log.info(f"Fetched {len(data)} timetable entries (dept={dept}, year={year})")
        return data
    except Exception as e:
        log.error(f"Timetable fetch error: {e}")
    return []


def fetch_roster(dept: str = "ALL", year: str = "ALL") -> list:
    """Fetch all students with WhatsApp details from Supabase."""
    try:
        client = get_supabase()
        q = client.table("students").select("*")
        if dept != "ALL": q = q.eq("department_code", dept)
        if year != "ALL": q = q.eq("year", year)
        res = q.execute()
        rows = res.data or []
        # Map to the column names the rest of this file already expects
        # (this file was written against the old sheet's header names).
        data = [{
            "Student Name":   r.get("student_name", ""),
            "Reg Number":     r.get("reg_number", ""),
            "Department":     r.get("department_code", ""),
            "Year":           r.get("year", ""),
            "WhatsApp Phone": r.get("whatsapp_phone", ""),
            "CallMeBot Key":  r.get("callmebot_apikey", ""),
        } for r in rows]
        log.info(f"Fetched {len(data)} roster entries (dept={dept}, year={year})")
        return data
    except Exception as e:
        log.error(f"Roster fetch error: {e}")
    return []


# ═════════════════════════════════════════════════════════════
# ██  WHATSAPP SENDER
# ═════════════════════════════════════════════════════════════

def send_whatsapp(phone: str, apikey: str, message: str) -> bool:
    """
    Send a single WhatsApp message via CallMeBot.
    phone must be in +256XXXXXXXXX format.
    Returns True if request was accepted (200 OK).
    """
    if not phone or not apikey:
        return False
    try:
        url = (
            f"https://api.callmebot.com/whatsapp.php"
            f"?phone={requests.utils.quote(phone)}"
            f"&text={requests.utils.quote(message)}"
            f"&apikey={requests.utils.quote(apikey)}"
        )
        r = _session.get(url, timeout=REQUEST_TIMEOUT)
        success = r.status_code == 200
        if success:
            log.info(f"✅ WhatsApp sent to {phone}")
        else:
            log.warning(f"⚠️ WhatsApp failed for {phone} — HTTP {r.status_code}")
        return success
    except requests.exceptions.Timeout:
        log.error(f"WhatsApp timeout for {phone}")
        return False
    except Exception as e:
        log.error(f"WhatsApp send error ({phone}): {e}")
        return False


def notify_group(dept: str, year: str, message: str) -> int:
    """
    Send a WhatsApp message to all opted-in students in a dept+year group.
    Returns count of successfully sent messages.
    Skips students without both phone and CallMeBot key saved.
    """
    students = fetch_roster(dept=dept, year=year)
    sent     = 0

    if not students:
        log.warning(f"No students found for {dept} Year {year}")
        return 0

    for student in students:
        # Support both capitalised and lowercase column names from GAS
        phone  = str(student.get("WhatsApp Phone", student.get("whatsapp phone", ""))).strip()
        apikey = str(student.get("CallMeBot Key",  student.get("callmebot key",  ""))).strip()

        if not phone or not apikey:
            continue  # Student hasn't set up WhatsApp — skip silently

        if send_whatsapp(phone, apikey, message):
            sent += 1
            time.sleep(CALLMEBOT_DELAY)  # Respect CallMeBot rate limit

    log.info(f"Group notify complete: {sent}/{len(students)} sent (dept={dept}, year={year})")
    return sent


# ═════════════════════════════════════════════════════════════
# ██  TIMETABLE LOGIC
# ═════════════════════════════════════════════════════════════

def get_today_name() -> str:
    """Return today's full day name in Uganda timezone."""
    tz  = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    return now.strftime("%A")  # e.g. "Monday"


def get_now_kampala() -> datetime:
    """Return current datetime in Uganda timezone."""
    return datetime.now(pytz.timezone(TIMEZONE))


def parse_lecture_time(time_str: str) -> datetime | None:
    """
    Parse a timetable Time string into today's datetime.
    Supports formats: '8:00 AM', '08:00', '8:00-10:00', '8AM'
    Returns None if unparseable.
    """
    if not time_str:
        return None

    # Take only the start time if range like '8:00-10:00' or '8:00 AM - 10:00 AM'
    start = time_str.strip().split("-")[0].strip()

    formats = ["%I:%M %p", "%H:%M", "%I %p", "%I:%M%p"]
    today   = get_now_kampala().date()

    for fmt in formats:
        try:
            t   = datetime.strptime(start, fmt)
            tz  = pytz.timezone(TIMEZONE)
            dt  = tz.localize(datetime(today.year, today.month, today.day, t.hour, t.minute))
            return dt
        except ValueError:
            continue

    log.warning(f"Could not parse time: '{time_str}'")
    return None


def get_todays_classes(dept: str = "ALL", year: str = "ALL") -> list:
    """
    Return all timetable entries for today, sorted by time.
    Filters by dept+year if provided.
    """
    today    = get_today_name()
    entries  = fetch_timetable(dept=dept, year=year)
    todays   = []

    for entry in entries:
        entry_day = str(entry.get("day", entry.get("Day", ""))).strip()
        if entry_day.lower() == today.lower():
            todays.append(entry)

    # Sort by parsed lecture time
    todays.sort(key=lambda e: parse_lecture_time(
        str(e.get("time", e.get("Time", "")))
    ) or datetime.max.replace(tzinfo=pytz.UTC))

    return todays


def get_all_dept_year_combos() -> list[tuple]:
    """
    Fetch all unique (dept, year) combinations from the full roster.
    Used to send morning reminders per group.
    """
    all_students = fetch_roster(dept="ALL", year="ALL")
    combos       = set()

    if not all_students:
        log.warning("No students found in roster")
        return []

    for s in all_students:
        dept = str(s.get("Department", s.get("department", ""))).strip().upper()
        year = str(s.get("Year",       s.get("year",       ""))).strip()
        if dept and year:
            combos.add((dept, year))

    log.info(f"Found {len(combos)} dept+year groups: {combos}")
    return list(combos)


# ═════════════════════════════════════════════════════════════
# ██  DECISION LOGIC — the "intelligence"
# ═════════════════════════════════════════════════════════════

def format_morning_message(dept: str, year: str, classes: list) -> str:
    """Build the morning timetable summary message."""
    today = get_today_name()

    if not classes:
        return (
            f"📅 Good morning, {dept} Year {year}!\n\n"
            f"🎉 No classes today ({today}). Enjoy your free day!\n\n"
            f"Open the Smart University App to check announcements."
        )

    lines = [f"📅 Good morning, {dept} Year {year}!",
             f"Here are your classes for {today}:\n"]

    for i, c in enumerate(classes, 1):
        course   = str(c.get("course",   c.get("Course",   ""))).strip()
        time_str = str(c.get("time",     c.get("Time",     ""))).strip()
        lecturer = str(c.get("lecturer", c.get("Lecturer", ""))).strip()
        venue    = str(c.get("venue",    c.get("Venue",    ""))).strip()

        line = f"{i}. {course} — {time_str}"
        if lecturer: line += f" ({lecturer})"
        if venue:    line += f" @ {venue}"
        lines.append(line)

    lines.append("\nOpen the Smart University App for full details.")
    return "\n".join(lines)


def format_reminder_message(dept: str, year: str, entry: dict, minutes: int) -> str:
    """Build a pre-lecture reminder message."""
    course   = str(entry.get("course",   entry.get("Course",   "Unknown"))).strip()
    time_str = str(entry.get("time",     entry.get("Time",     ""))).strip()
    lecturer = str(entry.get("lecturer", entry.get("Lecturer", ""))).strip()
    venue    = str(entry.get("venue",    entry.get("Venue",    ""))).strip()

    msg = (
        f"⏰ Lecture Reminder — {dept} Year {year}\n\n"
        f"📚 {course} starts in {minutes} minutes!\n"
        f"🕐 Time: {time_str}\n"
    )
    if lecturer: msg += f"👨‍🏫 Lecturer: {lecturer}\n"
    if venue:    msg += f"📍 Venue: {venue}\n"
    msg += "\nDon't be late! 🏃"
    return msg


# ═════════════════════════════════════════════════════════════
# ██  SCHEDULED JOBS
# ═════════════════════════════════════════════════════════════

def job_morning_reminders():
    """
    Fires at 6:30 AM every weekday.
    Sends each dept+year group their today's timetable summary.
    """
    log.info("=== JOB: Morning reminders ===")
    combos = get_all_dept_year_combos()

    if not combos:
        log.warning("No dept+year groups found — skipping morning reminders.")
        return

    for dept, year in combos:
        classes = get_todays_classes(dept=dept, year=year)
        message = format_morning_message(dept, year, classes)
        log.info(f"Morning reminder → {dept} Year {year} ({len(classes)} classes)")
        sent = notify_group(dept=dept, year=year, message=message)
        time.sleep(1)  # Small gap between groups


def job_pre_lecture_reminders():
    """
    Fires every 15 minutes throughout the day.
    Checks if any lecture starts in exactly 30 or 15 minutes
    and sends a reminder to that dept+year group.
    Duplicate-safe: only fires when the window matches.
    """
    log.info("=== JOB: Pre-lecture check ===")
    now    = get_now_kampala()
    combos = get_all_dept_year_combos()

    if not combos:
        log.warning("No dept+year groups found — skipping pre-lecture checks.")
        return

    for dept, year in combos:
        classes = get_todays_classes(dept=dept, year=year)

        for entry in classes:
            time_str    = str(entry.get("time", entry.get("Time", ""))).strip()
            lecture_dt  = parse_lecture_time(time_str)

            if not lecture_dt:
                continue

            minutes_away = (lecture_dt - now).total_seconds() / 60

            # Fire at 30-minute window (28–32 min to account for scheduler drift)
            if PRE_LECTURE_30 - 2 <= minutes_away <= PRE_LECTURE_30 + 2:
                log.info(f"30-min reminder: {entry.get('Course','?')} → {dept} Year {year}")
                message = format_reminder_message(dept, year, entry, PRE_LECTURE_30)
                notify_group(dept=dept, year=year, message=message)

            # Fire at 15-minute window
            elif PRE_LECTURE_15 - 2 <= minutes_away <= PRE_LECTURE_15 + 2:
                log.info(f"15-min reminder: {entry.get('Course','?')} → {dept} Year {year}")
                message = format_reminder_message(dept, year, entry, PRE_LECTURE_15)
                notify_group(dept=dept, year=year, message=message)


# ═════════════════════════════════════════════════════════════
# ██  MAIN — start the scheduler
# ═════════════════════════════════════════════════════════════

def main():
    tz        = pytz.timezone(TIMEZONE)
    scheduler = BlockingScheduler(timezone=tz)

    # Morning reminder — 6:30 AM, Monday to Saturday
    scheduler.add_job(
        job_morning_reminders,
        trigger=CronTrigger(
            hour=MORNING_HOUR, minute=MORNING_MINUTE,
            day_of_week="mon-sat", timezone=tz
        ),
        id="morning_reminders",
        name="Morning timetable summary",
        misfire_grace_time=300  # Run even if up to 5 min late
    )

    # Pre-lecture check — every 15 minutes, 7 AM to 8 PM on weekdays
    scheduler.add_job(
        job_pre_lecture_reminders,
        trigger=CronTrigger(
            hour="7-20", minute="0,15,30,45",
            day_of_week="mon-sat", timezone=tz
        ),
        id="pre_lecture_reminders",
        name="Pre-lecture reminders (30min & 15min)",
        misfire_grace_time=120
    )

    scheduler.add_job(
    send_master_ai_daily_report,
    trigger  = "cron",
    hour     = 8,
    minute   = 0,
    id       = "master_ai_daily_report",
    replace_existing = True
)

    log.info("════════════════════════════════════════")
    log.info("  Smart University WhatsApp Notifier")
    log.info(f"  Timezone : {TIMEZONE}")
    log.info(f"  Morning  : {MORNING_HOUR:02d}:{MORNING_MINUTE:02d} (Mon–Sat)")
    log.info(f"  Reminders: 30min & 15min before lectures")
    log.info(f"  Supabase : {SUPABASE_URL[:40] + '...' if SUPABASE_URL else 'NOT CONFIGURED'}")
    log.info("════════════════════════════════════════")
    log.info("Scheduler started. Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Notifier stopped.")

def send_master_ai_daily_report():
    """
    Called by APScheduler every morning at 8AM.
    Runs portal health check and sends report to Alia.
    """
    try:
        from ai_engine import MasterAIMonitor
        from database  import SheetDatabaseManager

        db      = SheetDatabaseManager()
        monitor = MasterAIMonitor(db)

        df_all      = db.fetch_all_roster()
        reps_list   = db.fetch_reps()
        all_feedback = db.fetch_all_feedback()
        all_anns    = db.fetch_all_announcements()

        report = monitor.generate_daily_report(
            df_all=df_all,
            reps_list=reps_list,
            all_feedback=all_feedback,
            all_anns=all_anns
        )

        monitor.send_alert(report, channel="both")
        print(f"[Notifier] Daily report sent successfully")

    except Exception as e:
        print(f"[Notifier] Daily report error: {e}")


if __name__ == "__main__":
    main()