-- ═══════════════════════════════════════════════════════════════════════
-- 002_notifications.sql
-- In-app notification system, backed by Supabase Realtime.
-- ═══════════════════════════════════════════════════════════════════════

create table if not exists notifications (
    id                  uuid primary key default gen_random_uuid(),
    student_reg         text not null references students(reg_number) on update cascade on delete cascade,
    announcement_id     uuid references announcements(id) on delete cascade,
    material_id         uuid references materials(id) on delete cascade,
    title               text not null,
    message             text not null,
    notification_type   text not null default 'announcement',
        -- announcement | material | timetable | feedback_reply | system
    is_read             boolean not null default false,
    created_at          timestamptz not null default now()
);

create index if not exists idx_notifications_student
    on notifications (student_reg, is_read, created_at desc);

-- Per-student notification channel preferences.
-- Kept separate from `students` so push-notification tokens / future
-- channels (email, SMS, browser push) can be added without altering
-- the students table.
create table if not exists notification_preferences (
    student_reg         text primary key references students(reg_number) on update cascade on delete cascade,
    in_app_enabled       boolean not null default true,
    whatsapp_enabled     boolean not null default false,
    push_enabled         boolean not null default false,   -- reserved for future browser/Android push
    push_token            text,                              -- reserved for future browser/Android push
    updated_at           timestamptz not null default now()
);

drop trigger if exists trg_notif_prefs_updated on notification_preferences;
create trigger trg_notif_prefs_updated before update on notification_preferences
    for each row execute function set_updated_at();

-- ─────────────────────────────────────────────────────────────
-- Enable Supabase Realtime on notifications (INSERT/UPDATE events)
-- so the Streamlit app can subscribe to new/changed rows.
-- ─────────────────────────────────────────────────────────────
alter table notifications replica identity full;

do $$
begin
    if not exists (
        select 1 from pg_publication_tables
        where pubname = 'supabase_realtime' and tablename = 'notifications'
    ) then
        alter publication supabase_realtime add table notifications;
    end if;
end $$;
