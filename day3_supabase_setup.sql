-- Day 3: Friends + Group base schema for Gaboda
-- Run this in Supabase SQL Editor (single script).

begin;

create extension if not exists pgcrypto;

-- 1) Friend relations (request -> accept flow)
create table if not exists public.friend_relations (
    id uuid primary key default gen_random_uuid(),
    requester_id text not null,
    addressee_id text not null,
    status text not null default 'pending' check (status in ('pending', 'accepted', 'rejected', 'blocked')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    responded_at timestamptz,
    check (requester_id <> addressee_id)
);

-- Prevent duplicate directed requests
create unique index if not exists ux_friend_relations_directed
    on public.friend_relations (requester_id, addressee_id);

-- Prevent duplicate relationships in reverse direction
create unique index if not exists ux_friend_relations_pair
    on public.friend_relations ((least(requester_id, addressee_id)), (greatest(requester_id, addressee_id)));

create index if not exists ix_friend_relations_requester_status
    on public.friend_relations (requester_id, status, created_at desc);

create index if not exists ix_friend_relations_addressee_status
    on public.friend_relations (addressee_id, status, created_at desc);

-- 2) Group base
create table if not exists public.travel_groups (
    id uuid primary key default gen_random_uuid(),
    owner_id text not null,
    group_name text not null,
    description text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists ix_travel_groups_owner
    on public.travel_groups (owner_id, created_at desc);

create table if not exists public.group_members (
    group_id uuid not null references public.travel_groups(id) on delete cascade,
    user_id text not null,
    role text not null default 'member' check (role in ('owner', 'member')),
    invite_status text not null default 'invited' check (invite_status in ('invited', 'joined', 'declined')),
    invited_by text,
    created_at timestamptz not null default now(),
    joined_at timestamptz,
    primary key (group_id, user_id)
);

create index if not exists ix_group_members_user
    on public.group_members (user_id, invite_status, created_at desc);

create index if not exists ix_group_members_group_status
    on public.group_members (group_id, invite_status);

-- 3) Updated_at helper trigger
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_friend_relations_updated_at on public.friend_relations;
create trigger trg_friend_relations_updated_at
before update on public.friend_relations
for each row execute function public.set_updated_at();

drop trigger if exists trg_travel_groups_updated_at on public.travel_groups;
create trigger trg_travel_groups_updated_at
before update on public.travel_groups
for each row execute function public.set_updated_at();

-- 4) RLS
alter table public.friend_relations enable row level security;
alter table public.travel_groups enable row level security;
alter table public.group_members enable row level security;

-- friend_relations policies
drop policy if exists "friend_select_mine" on public.friend_relations;
-- Read: only rows related to me
create policy "friend_select_mine"
on public.friend_relations
for select
to authenticated
using (
  requester_id = auth.uid()::text
  or addressee_id = auth.uid()::text
);

drop policy if exists "friend_insert_requester" on public.friend_relations;
-- Insert: I can send request only as requester
create policy "friend_insert_requester"
on public.friend_relations
for insert
to authenticated
with check (
  requester_id = auth.uid()::text
  and addressee_id <> auth.uid()::text
);

drop policy if exists "friend_update_participants" on public.friend_relations;
-- Update: requester/addressee can update their own relation row
create policy "friend_update_participants"
on public.friend_relations
for update
to authenticated
using (
  requester_id = auth.uid()::text
  or addressee_id = auth.uid()::text
)
with check (
  requester_id = auth.uid()::text
  or addressee_id = auth.uid()::text
);

drop policy if exists "friend_delete_participants" on public.friend_relations;
-- Delete: requester can cancel, addressee can remove/block cleanup
create policy "friend_delete_participants"
on public.friend_relations
for delete
to authenticated
using (
  requester_id = auth.uid()::text
  or addressee_id = auth.uid()::text
);

-- travel_groups policies
drop policy if exists "group_select_visible" on public.travel_groups;
create policy "group_select_visible"
on public.travel_groups
for select
to authenticated
using (
  owner_id = auth.uid()::text
  or exists (
    select 1
    from public.group_members gm
    where gm.group_id = travel_groups.id
      and gm.user_id = auth.uid()::text
      and gm.invite_status = 'joined'
  )
);

drop policy if exists "group_insert_owner_only" on public.travel_groups;
create policy "group_insert_owner_only"
on public.travel_groups
for insert
to authenticated
with check (
  owner_id = auth.uid()::text
);

drop policy if exists "group_update_owner_only" on public.travel_groups;
create policy "group_update_owner_only"
on public.travel_groups
for update
to authenticated
using (owner_id = auth.uid()::text)
with check (owner_id = auth.uid()::text);

drop policy if exists "group_delete_owner_only" on public.travel_groups;
create policy "group_delete_owner_only"
on public.travel_groups
for delete
to authenticated
using (owner_id = auth.uid()::text);

-- group_members policies
drop policy if exists "group_members_select_visible" on public.group_members;
create policy "group_members_select_visible"
on public.group_members
for select
to authenticated
using (
  user_id = auth.uid()::text
  or exists (
    select 1
    from public.travel_groups g
    where g.id = group_members.group_id
      and g.owner_id = auth.uid()::text
  )
  or exists (
    select 1
    from public.group_members gm
    where gm.group_id = group_members.group_id
      and gm.user_id = auth.uid()::text
      and gm.invite_status = 'joined'
  )
);

drop policy if exists "group_members_insert_owner" on public.group_members;
-- Owner invites members / inserts owner self-row
create policy "group_members_insert_owner"
on public.group_members
for insert
to authenticated
with check (
  exists (
    select 1
    from public.travel_groups g
    where g.id = group_members.group_id
      and g.owner_id = auth.uid()::text
  )
);

drop policy if exists "group_members_update_owner_or_self" on public.group_members;
-- Owner updates members OR invited user can accept/decline own invite
create policy "group_members_update_owner_or_self"
on public.group_members
for update
to authenticated
using (
  user_id = auth.uid()::text
  or exists (
    select 1
    from public.travel_groups g
    where g.id = group_members.group_id
      and g.owner_id = auth.uid()::text
  )
)
with check (
  user_id = auth.uid()::text
  or exists (
    select 1
    from public.travel_groups g
    where g.id = group_members.group_id
      and g.owner_id = auth.uid()::text
  )
);

drop policy if exists "group_members_delete_owner" on public.group_members;
create policy "group_members_delete_owner"
on public.group_members
for delete
to authenticated
using (
  exists (
    select 1
    from public.travel_groups g
    where g.id = group_members.group_id
      and g.owner_id = auth.uid()::text
  )
);

commit;
