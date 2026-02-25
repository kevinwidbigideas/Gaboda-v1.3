begin;

alter table public.travel_groups enable row level security;
alter table public.group_members enable row level security;

-- 기존 정책들을 깨끗이 비웁니다.
drop policy if exists "group_select_visible" on public.travel_groups;
drop policy if exists "group_insert_owner_only" on public.travel_groups;
drop policy if exists "group_update_owner_only" on public.travel_groups;
drop policy if exists "group_delete_owner_only" on public.travel_groups;

drop policy if exists "group_members_select_visible" on public.group_members;
drop policy if exists "group_members_insert_owner" on public.group_members;
drop policy if exists "group_members_update_owner_or_self" on public.group_members;
drop policy if exists "group_members_delete_owner" on public.group_members;

--------------------------------------------------------------------------------
-- 1. travel_groups
--------------------------------------------------------------------------------
create policy "group_select_visible"
on public.travel_groups
for select
using (
  owner_id = auth.uid()::text
  or id in (
    select gm.group_id 
    from public.group_members gm
    where gm.user_id = auth.uid()::text
  )
);

create policy "group_insert_owner_only"
on public.travel_groups
for insert
with check (
  owner_id = auth.uid()::text
);

create policy "group_update_owner_only"
on public.travel_groups
for update
using (owner_id = auth.uid()::text)
with check (owner_id = auth.uid()::text);

create policy "group_delete_owner_only"
on public.travel_groups
for delete
using (owner_id = auth.uid()::text);


--------------------------------------------------------------------------------
-- 2. group_members
--------------------------------------------------------------------------------
create policy "group_members_select_visible"
on public.group_members
for select
using (
  user_id = auth.uid()::text
  or group_id in (
    select gm.group_id 
    from public.group_members gm
    where gm.user_id = auth.uid()::text
  )
);

create policy "group_members_insert_owner"
on public.group_members
for insert
with check (
  -- 그룹장(owner)이 자신이나 그룹원을 인서트할 때 허용
  user_id = auth.uid()::text
  or group_id in (
    select tg.id 
    from public.travel_groups tg
    where tg.owner_id = auth.uid()::text
  )
);

create policy "group_members_update_owner_or_self"
on public.group_members
for update
using (
  user_id = auth.uid()::text
  or group_id in (
    select tg.id 
    from public.travel_groups tg
    where tg.owner_id = auth.uid()::text
  )
)
with check (
  user_id = auth.uid()::text
  or group_id in (
    select tg.id 
    from public.travel_groups tg
    where tg.owner_id = auth.uid()::text
  )
);

create policy "group_members_delete_owner"
on public.group_members
for delete
using (
  user_id = auth.uid()::text
  or group_id in (
    select tg.id 
    from public.travel_groups tg
    where tg.owner_id = auth.uid()::text
  )
);

commit;
