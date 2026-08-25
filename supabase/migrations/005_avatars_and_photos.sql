-- ═══════════════════════════════════════════════════════════════════════
-- 005_avatars_and_photos.sql
-- Add avatar_url columns and storage bucket for user profile photos
-- ═══════════════════════════════════════════════════════════════════════

-- 1. Add avatar_url column to students if not exists
alter table students 
    add column if not exists avatar_url text not null default '';

-- 2. Add avatar_url column to class_representatives if not exists
alter table class_representatives 
    add column if not exists avatar_url text not null default '';

-- 3. Add storage bucket for user profile avatars
insert into storage.buckets (id, name, public)
values ('avatars', 'avatars', true)
on conflict (id) do nothing;

-- 4. Set public read access policy for avatars
drop policy if exists "Public read avatars" on storage.objects;
create policy "Public read avatars"
    on storage.objects for select
    using (bucket_id = 'avatars');
