-- ═══════════════════════════════════════════════════════════════════════
-- 001_initial_schema.sql
-- Smart University App — Core relational schema (Google Sheets replacement)
-- Run this in the Supabase SQL Editor, or via `supabase db push`.
-- ═══════════════════════════════════════════════════════════════════════

create extension if not exists "pgcrypto";   -- for gen_random_uuid()

-- ─────────────────────────────────────────────────────────────
-- DEPARTMENTS
-- ─────────────────────────────────────────────────────────────
create table if not exists departments (
    code        text primary key,                 -- e.g. 'MEC'
    name        text not null,                     -- e.g. 'Mechanical Engineering'
    color       text not null default '#1a56db',
    light       text not null default '#dbeafe',
    courses     text[] not null default '{}',      -- e.g. {BMEC,BBPE}
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- ─────────────────────────────────────────────────────────────
-- STUDENTS  (the former "Roster" sheet)
-- ─────────────────────────────────────────────────────────────
create table if not exists students (
    id                uuid primary key default gen_random_uuid(),
    reg_number        text not null unique,
    student_name      text not null,
    course_code       text not null default 'UNASSIGNED',
    contact           text not null default '',
    whatsapp_phone    text not null default '',
    callmebot_apikey  text not null default '',
    assigned_group    text not null default 'Unassigned',
    department_code   text references departments(code) on update cascade on delete set null,
    year              text not null default 'Year 1',
    pin_hash          text,                         -- pbkdf2_hmac hash, "salt$hash"
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);
create index if not exists idx_students_dept_year on students (department_code, year);
create index if not exists idx_students_reg on students (reg_number);

-- ─────────────────────────────────────────────────────────────
-- CLASS REPRESENTATIVES
-- ─────────────────────────────────────────────────────────────
create table if not exists class_representatives (
    id                uuid primary key default gen_random_uuid(),
    department_code   text not null references departments(code) on update cascade on delete cascade,
    year              text not null,
    rep_name          text not null,
    rep_reg           text not null default '',
    password_hash     text not null,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now(),
    unique (department_code, year)
);

-- ─────────────────────────────────────────────────────────────
-- ANNOUNCEMENTS  (department_code / year = NULL  ⇒  "ALL")
-- ─────────────────────────────────────────────────────────────
create table if not exists announcements (
    id                uuid primary key default gen_random_uuid(),
    title             text not null default 'Announcement',
    content           text not null,
    priority          text not null default 'Normal',   -- Normal | Urgent
    department_code   text references departments(code) on update cascade on delete cascade,
    year              text,
    created_by        text not null default 'Class Rep',
    notify_whatsapp   boolean not null default false,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);
create index if not exists idx_announcements_scope on announcements (department_code, year, created_at desc);

-- ─────────────────────────────────────────────────────────────
-- MATERIALS  (files live in Supabase Storage bucket "materials")
-- ─────────────────────────────────────────────────────────────
create table if not exists materials (
    id                uuid primary key default gen_random_uuid(),
    title             text not null,
    description       text not null default '',
    file_path         text not null,      -- storage object path
    mime_type         text not null default 'application/octet-stream',
    department_code   text references departments(code) on update cascade on delete cascade,
    year              text,
    uploaded_by       text not null default 'Class Rep',
    notify_whatsapp   boolean not null default false,
    created_at        timestamptz not null default now()
);
create index if not exists idx_materials_scope on materials (department_code, year, created_at desc);

-- ─────────────────────────────────────────────────────────────
-- COURSE-UNIT GROUPS  (per-student, per-course-unit group allocation)
-- ─────────────────────────────────────────────────────────────
create table if not exists course_unit_groups (
    id                uuid primary key default gen_random_uuid(),
    student_reg       text not null references students(reg_number) on update cascade on delete cascade,
    department_code   text,
    year              text,
    course_unit       text not null,
    group_name        text not null,
    updated_at        timestamptz not null default now(),
    unique (student_reg, course_unit)
);

-- ─────────────────────────────────────────────────────────────
-- FEEDBACK  (student → class rep)
-- ─────────────────────────────────────────────────────────────
create table if not exists feedback (
    id                uuid primary key default gen_random_uuid(),
    reg_number        text not null,
    student_name      text not null,
    message           text not null,
    department_code   text,
    year              text,
    status            text not null default 'Pending',   -- Pending | Reviewed
    created_at        timestamptz not null default now()
);
create index if not exists idx_feedback_scope on feedback (department_code, year, created_at desc);
create index if not exists idx_feedback_reg on feedback (reg_number);

-- ─────────────────────────────────────────────────────────────
-- REP REPLIES  (class rep → student, in reply to feedback)
-- ─────────────────────────────────────────────────────────────
create table if not exists rep_replies (
    id                uuid primary key default gen_random_uuid(),
    reg_number        text not null,
    student_name      text not null,
    rep_name          text not null default 'Class Rep',
    message           text not null,
    department_code   text,
    year              text,
    read_status       text not null default 'Unread',    -- Unread | Read
    created_at        timestamptz not null default now()
);
create index if not exists idx_rep_replies_reg on rep_replies (reg_number, created_at desc);

-- ─────────────────────────────────────────────────────────────
-- TIMETABLE
-- ─────────────────────────────────────────────────────────────
create table if not exists timetable (
    id                uuid primary key default gen_random_uuid(),
    department_code   text not null,
    year              text not null,
    day               text not null,
    time              text not null,
    course            text not null,
    lecturer          text not null default '',
    color             text not null default '',
    entry_type        text not null default 'Weekly',
    created_at        timestamptz not null default now(),
    unique (department_code, year, day, time)
);

-- ─────────────────────────────────────────────────────────────
-- CHAT HISTORY  (AI Study Assistant)
-- ─────────────────────────────────────────────────────────────
create table if not exists chat_history (
    id                bigint generated always as identity primary key,
    reg_number        text not null,
    role              text not null,           -- user | assistant
    message           text not null,
    created_at        timestamptz not null default now()
);
create index if not exists idx_chat_history_reg on chat_history (reg_number, created_at desc);

-- ─────────────────────────────────────────────────────────────
-- MASTER AI MEMORY  (Super Admin master AI persistent memory)
-- ─────────────────────────────────────────────────────────────
create table if not exists ai_memory (
    id                bigint generated always as identity primary key,
    mem_type          text not null,
    key               text not null,
    value             text not null,
    updated_at        timestamptz not null default now(),
    unique (mem_type, key)
);

-- ─────────────────────────────────────────────────────────────
-- FUNCTION LIBRARY  (Super Admin — saved automation snippets)
-- ─────────────────────────────────────────────────────────────
create table if not exists function_library (
    id                uuid primary key default gen_random_uuid(),
    name              text not null unique,
    script            text not null default '',
    description       text not null default '',
    updated_at        timestamptz not null default now()
);

-- ─────────────────────────────────────────────────────────────
-- APP CONFIG  (generic key/value settings store)
-- ─────────────────────────────────────────────────────────────
create table if not exists app_config (
    key               text primary key,
    value             text not null default '',
    description       text not null default '',
    updated_at        timestamptz not null default now()
);

-- ─────────────────────────────────────────────────────────────
-- SLOTS  (configurable quick-action / AI slot system)
-- ─────────────────────────────────────────────────────────────
create table if not exists slots (
    id                text primary key,
    audience          text not null default 'student',   -- student | rep | admin
    department_code   text not null default 'ALL',
    year              text not null default 'ALL',
    active            boolean not null default true,
    slot_data         jsonb not null default '{}'::jsonb,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);
create index if not exists idx_slots_audience on slots (audience, active);

-- ─────────────────────────────────────────────────────────────
-- updated_at auto-touch trigger (generic, reused by later migrations)
-- ─────────────────────────────────────────────────────────────
create or replace function set_updated_at() returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_departments_updated on departments;
create trigger trg_departments_updated before update on departments
    for each row execute function set_updated_at();

drop trigger if exists trg_students_updated on students;
create trigger trg_students_updated before update on students
    for each row execute function set_updated_at();

drop trigger if exists trg_reps_updated on class_representatives;
create trigger trg_reps_updated before update on class_representatives
    for each row execute function set_updated_at();

drop trigger if exists trg_announcements_updated on announcements;
create trigger trg_announcements_updated before update on announcements
    for each row execute function set_updated_at();
