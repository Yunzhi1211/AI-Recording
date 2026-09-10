-- Iris Studio community. Run once in Supabase → SQL editor.
-- First-time projects: this only creates a table and access rules.
-- It does not delete your posts.

create table if not exists public.community_posts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users (id) on delete set null,
  field text not null default 'school',
  title text not null,
  body text not null,
  is_anonymous boolean not null default false,
  created_at timestamptz not null default now(),
  constraint community_posts_body_len check (char_length(btrim(body)) between 8 and 4000),
  constraint community_posts_title_len check (char_length(btrim(title)) between 1 and 80),
  constraint community_posts_field_ok check (field in ('school', 'corp', 'personal'))
);

create index if not exists community_posts_field_created
  on public.community_posts (field, created_at desc);

alter table public.community_posts enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'community_posts'
      and policyname = 'community_posts_read'
  ) then
    create policy community_posts_read
      on public.community_posts
      for select
      using (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'community_posts'
      and policyname = 'community_posts_insert_named'
  ) then
    create policy community_posts_insert_named
      on public.community_posts
      for insert
      to authenticated
      with check (
        is_anonymous = false
        and user_id = auth.uid()
      );
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'community_posts'
      and policyname = 'community_posts_insert_anon'
  ) then
    create policy community_posts_insert_anon
      on public.community_posts
      for insert
      to anon
      with check (
        is_anonymous = true
        and user_id is null
      );
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'community_posts'
      and policyname = 'community_posts_delete_own'
  ) then
    create policy community_posts_delete_own
      on public.community_posts
      for delete
      to authenticated
      using (user_id = auth.uid());
  end if;
end
$$;
