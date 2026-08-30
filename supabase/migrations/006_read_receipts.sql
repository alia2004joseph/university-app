-- ═══════════════════════════════════════════════════════════════════════
-- 006_read_receipts.sql
-- Tracking student engagement: announcement reads and material access
-- ═══════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────
-- 1. ANNOUNCEMENT READS
-- ─────────────────────────────────────────────────────────────
create table if not exists announcement_reads (
    id                  uuid primary key default gen_random_uuid(),
    announcement_id     uuid references announcements(id) on delete cascade,
    student_reg         text not null references students(reg_number) on update cascade on delete cascade,
    read_at             timestamptz not null default now(),
    unique (announcement_id, student_reg)
);

create index if not exists idx_ann_reads_ann_id on announcement_reads (announcement_id);
create index if not exists idx_ann_reads_student on announcement_reads (student_reg);

-- ─────────────────────────────────────────────────────────────
-- 2. MATERIAL ACCESS LOGS
-- ─────────────────────────────────────────────────────────────
create table if not exists material_access_logs (
    id                  uuid primary key default gen_random_uuid(),
    material_id         uuid references materials(id) on delete cascade,
    student_reg         text not null references students(reg_number) on update cascade on delete cascade,
    action_type         text not null default 'view',   -- view | preview | download | ai_study
    accessed_at         timestamptz not null default now(),
    unique (material_id, student_reg)
);

create index if not exists idx_mat_access_mat_id on material_access_logs (material_id);
create index if not exists idx_mat_access_student on material_access_logs (student_reg);

-- ─────────────────────────────────────────────────────────────
-- 3. ROW LEVEL SECURITY
-- ─────────────────────────────────────────────────────────────
alter table announcement_reads enable row level security;
alter table material_access_logs enable row level security;
