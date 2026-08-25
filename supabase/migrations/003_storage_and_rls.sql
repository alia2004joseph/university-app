-- ═══════════════════════════════════════════════════════════════════════
-- 003_storage_and_rls.sql
-- Supabase Storage bucket for materials + Row Level Security.
--
-- ARCHITECTURE NOTE (read this before editing policies):
-- This Streamlit app is a server-rendered application: all Supabase calls
-- are made from the trusted Python server process using the SUPABASE
-- SERVICE ROLE key (never sent to the browser). The service role key
-- bypasses RLS by design, and the app enforces who-can-see-what in its
-- own Python service layer (database/*.py), because student/rep/admin
-- login uses this app's own PIN/password system, not Supabase Auth.
--
-- The RLS policies below are defense-in-depth: they make sure that if
-- the anon/public key were ever used directly (e.g. a future browser
-- integration), it could not read or write anything by default. Only
-- the service role (used by the Streamlit backend) has access.
-- ═══════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────
-- STORAGE BUCKET FOR LEARNING MATERIALS
-- ─────────────────────────────────────────────────────────────
insert into storage.buckets (id, name, public)
values ('materials', 'materials', true)
on conflict (id) do nothing;

-- Public read of files (materials are non-sensitive course content).
-- Uploads/deletes are only ever performed by the Streamlit backend
-- using the service role key, so no INSERT/UPDATE/DELETE policy is
-- granted to anon/authenticated here.
drop policy if exists "Public read materials" on storage.objects;
create policy "Public read materials"
    on storage.objects for select
    using (bucket_id = 'materials');

-- ─────────────────────────────────────────────────────────────
-- ROW LEVEL SECURITY — enable on every application table
-- ─────────────────────────────────────────────────────────────
alter table departments              enable row level security;
alter table students                 enable row level security;
alter table class_representatives    enable row level security;
alter table announcements            enable row level security;
alter table materials                enable row level security;
alter table course_unit_groups       enable row level security;
alter table feedback                 enable row level security;
alter table rep_replies              enable row level security;
alter table timetable                enable row level security;
alter table notifications            enable row level security;
alter table notification_preferences enable row level security;
alter table chat_history             enable row level security;
alter table ai_memory                enable row level security;
alter table function_library         enable row level security;
alter table app_config               enable row level security;
alter table slots                    enable row level security;

-- Departments and timetable are non-sensitive/public read-only reference
-- data, so we allow anon SELECT for them (handy if you ever query them
-- directly from a browser/dashboard). Everything else defaults to
-- "no policy ⇒ no anon/authenticated access", which is intentional:
-- the Streamlit backend (service role) is the only writer/reader.
drop policy if exists "Public read departments" on departments;
create policy "Public read departments" on departments
    for select using (true);

drop policy if exists "Public read timetable" on timetable;
create policy "Public read timetable" on timetable
    for select using (true);

-- If you later add Supabase Auth (e.g. a browser client for students),
-- replace the tables above with policies such as:
--
--   create policy "Students read own notifications"
--       on notifications for select
--       using (student_reg = (auth.jwt() ->> 'reg_number'));
--
-- and issue a custom JWT (or map auth.uid() to a students row) at login.
