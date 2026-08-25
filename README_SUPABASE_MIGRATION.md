# Smart University App — Google Sheets → Supabase Migration

This document is the full deliverable for the migration: what changed, the
new database schema, exact setup steps, and how to test everything.

Your app's **features, pages, navigation and UI are unchanged**. Only the
backend moved from Google Sheets + Apps Script to Supabase (Postgres +
Storage + Realtime).

---

## A. Architecture summary

**Before:**
```
Streamlit  →  Google Apps Script (WEBHOOK_URL)  →  Google Sheets
```

**After:**
```
Streamlit  →  database/ (Python service layer)  →  Supabase
                                                      ├── PostgreSQL  (data)
                                                      ├── Storage     (materials/PDFs)
                                                      └── Realtime    (notifications, near-instant)
```

Every `db.xxx()` call your pages already make (`db.fetch_roster()`,
`db.post_announcement()`, `db.fetch_materials()`, ...) still exists with
the exact same name and signature — only what happens *inside* it changed.
`student.py`, `class_rep.py`, `Superadmin.py` and `ai_engine.py` needed
**no changes** to their business logic. The one addition is a 🔔
notification bell on the student dashboard.

**Authentication:** kept as-is. Students log in with Reg Number + PIN,
Class Reps with Department + Year + password, Super Admin with a
password — all stored in this app's own tables now (PINs/passwords are
hashed with PBKDF2, whereas the old Sheet stored PINs in plaintext). This
app's Python backend is the trusted party — it holds the Supabase
**service role key** in `st.secrets` and never sends it to the browser —
so it enforces "students can't see other students' data" itself, the same
way it always did. Supabase Row Level Security is enabled on every table
as defense-in-depth (see migration `003`) in case the anon key is ever
used directly in the future.

---

## B. Database schema

All in `supabase/migrations/001_initial_schema.sql` (+ `002`, `003`, `004`):

| Table | Replaces sheet | Notes |
|---|---|---|
| `departments` | Departments | code, name, colors, course list |
| `students` | Roster | reg_number unique, **email unique + format-checked**, PIN hashed, FK → departments |
| `class_representatives` | Reps | one per (department, year), password hashed |
| `announcements` | Announcements | `department_code`/`year` NULL = "ALL" |
| `materials` | Materials | metadata only; files live in Storage bucket `materials` |
| `course_unit_groups` | (group columns) | per-student, per-course-unit group |
| `feedback` | Feedback | student → rep |
| `rep_replies` | RepReplies | rep → student, triggers a notification |
| `timetable` | Timetable | unique per (dept, year, day, time) |
| `notifications` | *(new)* | one row per student per event; realtime-enabled |
| `notification_preferences` | *(new)* | reserved for future push notifications |
| `chat_history` | ChatHistory | AI Study Assistant |
| `ai_memory` | MasterAIMemory | Super Admin master AI |
| `function_library` | FunctionLibrary | saved snippets (reference only now) |
| `app_config` | Config | generic key/value settings |
| `slots` | Slots | configurable AI/quick-action buttons |

Relationships: `students.department_code → departments.code`,
`class_representatives.department_code → departments.code`,
`announcements/materials.department_code → departments.code`,
`notifications.student_reg → students.reg_number`,
`notifications.announcement_id → announcements.id`,
`course_unit_groups.student_reg → students.reg_number`.

---

## Email address requirement + "check the app" email notifications

Two separate things were added, both live in `supabase/migrations/004_student_email.sql`:

**1. Email is now required at registration.**
`student.py`'s registration form has a new **Email Address** field that's
validated client-side (`database/students.py::is_valid_email`) *and*
enforced by a Postgres `CHECK` constraint + a case-insensitive unique
index, so it can't be bypassed even by a direct API call. Existing
students who registered before this change will simply have `email = NULL`
until they add one from **Profile → Update Email Address** (also added).

**2. Announcements/materials now also send a short email — deliberately
NOT the full content.**
When a Class Rep posts an announcement (or uploads a material), in
addition to the in-app 🔔 notification, every affected student with an
email on file gets a short email like:

> 📢 New Announcement — Smart University App
>
> [first ~140 characters of the announcement as a preview]
>
> This is just a preview — please open the Smart University App to read
> the full announcement and stay up to date: `<APP_URL>`

This is intentional, per your requirement: the email is a *nudge*, not a
replacement for the app, so students still have to open it to read the
full announcement, reply to feedback, view materials, etc. This lives in
`database/email_notify.py` and plugs into the same fan-out that already
creates in-app notifications (`database/notifications.py`) — no change
needed anywhere else.

**Configuration is optional and fails silently.** If you don't set the
`SMTP_*` secrets, `is_email_configured()` returns `False` and every send
function just returns `0`/`False` (logged, never raised) — exactly like
the existing WhatsApp channel. See `.streamlit/secrets.toml.example` for
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`,
and `APP_URL` (used in the "open the app" link). Gmail works well here
with an [App Password](https://myaccount.google.com/apppasswords).

---

## C. Files changed

- `requirements.txt` — added `supabase`, `python-dotenv`
- `cache.py` — rewritten to call the new `database/` service layer instead of the GAS webhook (same function names/TTLs)
- `config.py` — `load_departments()` now reads Supabase instead of the webhook, with a hardcoded fallback if Supabase isn't configured yet
- `student.py` — added the 🔔 notification bell, a required **Email Address** field on registration (validated), and a Profile → **Update Email Address** section
- `database/students.py` — email validation (`is_valid_email`), `register_student`/`update_email` now handle/enforce it
- `database/notifications.py` — announcement/material/single-student notifications now also trigger a short "check the app" teaser email (best-effort, non-fatal)
- `notifier.py` — its data layer (`fetch_timetable`, `fetch_roster`) now reads Supabase via env vars instead of the GAS webhook; WhatsApp/CallMeBot logic and the reminder scheduling logic are untouched
- `.gitignore` — keeps `.streamlit/secrets.toml.example` trackable while still ignoring the real secrets file; ignores `.env`

## D. Files created

- `database/` package (replaces the old single `database.py`):
  `__init__.py` (facade — same public API as before), `supabase_client.py`,
  `students.py`, `departments.py`, `announcements.py`, `materials.py`,
  `feedback.py`, `rep_replies.py`, `reps.py`, `timetable.py`,
  `notifications.py`, `whatsapp.py`, `chat.py`, `ai_memory.py`,
  `config_store.py`, `slots.py`, `admin_tools.py`
- `notifications_ui.py` — the 🔔 bell widget
- `database/email_notify.py` — SMTP-based "check the app" teaser emails (optional, graceful no-op if unconfigured)
- `supabase/migrations/001_initial_schema.sql`, `002_notifications.sql`, `003_storage_and_rls.sql`, `004_student_email.sql`
- `supabase/seed_demo_data.py` — optional demo data + reset
- `.streamlit/secrets.toml.example`
- `.env.example` — for the standalone `notifier.py` process

## E. Files removed / deprecated

- `database.py` (single file) — replaced by the `database/` package
- The `WEBHOOK_URL` / Google Apps Script endpoint is no longer called anywhere
- `GASEditor` inside `ai_engine.py` is now inert (there's no more Apps
  Script backend for it to edit). It already degrades gracefully with a
  friendly message when `GOOGLE_SERVICE_ACCOUNT`/`APPS_SCRIPT_ID` aren't
  set — left in place untouched per the "don't remove AI features"
  instruction, but you can safely delete it later.
- `admin_tools.py`'s `create_sheet` / `rename_sheet` / `delete_sheet` /
  `write_row` intentionally return a friendly "not supported" message —
  schema changes now go through SQL migrations, not runtime DDL from the
  UI (see that file's docstring for the reasoning).

---

## ⚠️ Credentials found in your upload — rotate these now

`.streamlit/secrets.toml` in your uploaded project contained **real, live
keys**: `GEMINI_API_KEY_1..5`, `CLOUDFLARE_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`,
`GROQ_API_KEY`, `MISTRAL_API_KEY`, `HUGGINGFACE_TOKEN`, `GITHUB_TOKEN`, and
a `GOOGLE_SERVICE_ACCOUNT` private key. I did not copy any of these values
into any file I created. **Rotate all of them**, then put the new values
into your real `.streamlit/secrets.toml` (which stays out of git).

---

## F. Setup instructions

### 1. Create the Supabase project
Go to [supabase.com](https://supabase.com) → New Project. Note your
project URL and keys from **Settings → API**.

### 2. Run the migrations
Easiest: Supabase Dashboard → **SQL Editor** → paste and run, in order:
1. `supabase/migrations/001_initial_schema.sql`
2. `supabase/migrations/002_notifications.sql`
3. `supabase/migrations/003_storage_and_rls.sql`
4. `supabase/migrations/004_student_email.sql`

(Or, if you use the Supabase CLI: `supabase db push` from the project root.)

### 3. Configure Storage
Migration `003` already creates a public `materials` bucket and its read
policy — nothing else to do. Confirm it in **Storage** in the dashboard.

### 4. Configure Realtime
Migration `002` already adds the `notifications` table to the
`supabase_realtime` publication. Confirm under **Database → Replication**
that `notifications` is listed.

### 5. Add Streamlit secrets
Copy the example and fill in real values:
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```
At minimum set:
```toml
SUPABASE_URL = "https://xxxxx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJ..."   # Settings → API → service_role (secret)
```
Keep the other keys (Gemini, etc.) as needed for AI features — with your
**rotated** values, not the old ones.

### 6. (Optional) Seed demo data
```bash
pip install -r requirements.txt
export SUPABASE_URL=...
export SUPABASE_SERVICE_ROLE_KEY=...
python supabase/seed_demo_data.py
```
To wipe it later: `python supabase/seed_demo_data.py --reset`

### 7. Start the application
```bash
pip install -r requirements.txt
streamlit run app.py
```

### 8. (Optional) Run the WhatsApp reminder notifier
This is a separate 24/7 process (Railway/Render/VPS), not part of the
Streamlit app:
```bash
cp .env.example .env   # fill in SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY
python notifier.py
```

---

## G. Testing instructions

### Student
1. Log in with a seeded reg number + PIN (or register a new student via the Super Admin/Class Rep flow).
2. Dashboard loads; **🔔 Notifications** appears under the welcome banner.
3. View announcements, materials (download should work — files come from the public Storage bucket now).
4. Submit feedback; check a Class Rep reply produces a notification.
5. Check groups/timetable render.
6. Try the AI Study Assistant — chat history now persists via `chat_history` in Supabase.

### Class Representative
1. Log in with department + year + password.
2. Post an announcement → confirm it appears in the `announcements` table in Supabase, and rows appear in `notifications` for every student in that dept/year.
3. Upload a material → confirm a file appears in Storage → `materials` bucket, and a `notifications` row of type `material` is created.
4. Reply to a feedback item → confirm the student gets a `feedback_reply` notification.

### Admin
1. Log in as Super Admin.
2. Manage departments/roster/reps — confirm changes hit Supabase.
3. Confirm broadcast announcements (dept = "ALL") reach everyone.

### The critical end-to-end test (per the migration brief, section 25)
1. Seed/register two students in the same dept+year (e.g. `MEC / Year 1`).
2. Log in as Student A in one browser tab.
3. Log in as the Class Rep for `MEC / Year 1` in another tab.
4. Class Rep posts "Test Announcement".
5. In Supabase Table Editor: confirm one row in `announcements`, and **one `notifications` row per MEC/Year 1 student** (both students, not students in other departments).
6. Within ~5 seconds, Student A's 🔔 bell count updates (no manual refresh) — see "Known limitations" below for exactly what "near-realtime" means here.
7. Student A opens the notification → content matches the announcement → marking it read flips `is_read = true` in Supabase.
8. Confirm a student in a *different* department does **not** see this notification.

---

## H. Known limitations (read this — it's the honest part)

**Streamlit reruns its whole script on every interaction and has no
persistent event loop of its own.** A raw Supabase Realtime subscription
is a long-lived websocket — you can't simply `await` it inside a normal
Streamlit script run. This app uses the supported, robust pattern instead:
the notification bell is an `st.fragment(run_every=5s)` that re-queries
Supabase's lightweight unread-count/list endpoints on its own short timer,
independent of the rest of the page. This is **near-real-time (a few
seconds), not an instant push**, but it:
- doesn't reload the whole page (only the bell fragment reruns),
- is querying Supabase (not a spreadsheet),
- and is the pattern Streamlit itself documents for this kind of "live" UI.

If you later want true push-on-write (sub-second, no polling), the next
step is a small always-on side process (or a Supabase Edge Function) that
holds the real websocket subscription and pushes to connected browsers —
Streamlit's `st.fragment` polling was chosen here because it's simple,
has zero extra moving parts, and is safe to ship without live credentials
to test against. The `notification_preferences.push_token`/`push_enabled`
columns are already in the schema so browser/Android push can be layered
on later without a schema change.

**Other things worth knowing:**
- The `materials` Storage bucket is public (course content isn't
  sensitive); if that's ever untrue for your use case, switch to signed
  URLs in `database/materials.py::_public_url`.
- RLS policies default-deny the anon key on most tables since this app
  doesn't use Supabase Auth; if you build a separate browser client later,
  you'll want to issue it a scoped JWT and add matching policies (a
  starting example is commented in migration `003`).
- `GASEditor` (Super Admin AI code-editing tool) is now inert since there's
  no Apps Script backend left to edit against — it fails gracefully.
