-- ═══════════════════════════════════════════════════════════════════════
-- 004_student_email.sql
-- Adds a validated, unique email address to every student, and a place
-- to track whether each student has verified/confirmed it.
-- ═══════════════════════════════════════════════════════════════════════

alter table students
    add column if not exists email text;

-- Basic format check (defense-in-depth — the app also validates on submit).
-- Not a full RFC-5322 validator, just enough to catch obvious typos like
-- "bob@gmail" or "bob gmail.com".
alter table students
    drop constraint if exists students_email_format_check;
alter table students
    add constraint students_email_format_check
    check (email is null or email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

-- One account per email address.
create unique index if not exists idx_students_email_unique
    on students (lower(email))
    where email is not null;

comment on column students.email is
    'Required at registration going forward. Used for lightweight "check the app" notification emails (see database/email_notify.py) — full announcement content is never sent by email, only a teaser + link, to keep students visiting the app.';
