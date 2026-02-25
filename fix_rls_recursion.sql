-- Fix infinite recursion in travel_groups and group_members

begin;

-- 1) Use a SECURITY DEFINER function to bypass RLS recursion
create or replace function public.has_group_access(check_group_id uuid, check_user_id text)
returns boolean
language sql
security definer
set search_path = public
as $$
  select exists (
    select 1 from travel_groups
    where id = check_group_id and owner_id = check_user_id
  ) or exists (
    select 1 from group_members
    where group_id = check_group_id and user_id = check_user_id
  );
$$;

create or replace function public.is_group_owner(check_group_id uuid, check_user_id text)
returns boolean
language sql
security definer
set search_path = public
as $$
  select exists (
    select 1 from travel_groups
    where id = check_group_id and owner_id = check_user_id
  );
$$;

-- 2) Drop all recursive policies
drop policy if exists "group_select_visible" on public.travel_groups;
drop policy if exists "group_members_select_visible" on public.group_members;
drop policy if exists "group_members_insert_owner" on public.group_members;
drop policy if exists "group_members_update_owner_or_self" on public.group_members;
drop policy if exists "group_members_delete_owner" on public.group_members;

-- 3) Re-create policies using the functions
create policy "group_select_visible"
on public.travel_groups
for select
to authenticated
using (
  public.has_group_access(id, auth.uid()::text)
);

create policy "group_members_select_visible"
on public.group_members
for select
to authenticated
using (
  user_id = auth.uid()::text
  or 
  public.has_group_access(group_id, auth.uid()::text)
);

create policy "group_members_insert_owner"
on public.group_members
for insert
to authenticated
with check (
  public.is_group_owner(group_id, auth.uid()::text)
);

create policy "group_members_update_owner_or_self"
on public.group_members
for update
to authenticated
using (
  user_id = auth.uid()::text
  or 
  public.is_group_owner(group_id, auth.uid()::text)
)
with check (
  user_id = auth.uid()::text
  or 
  public.is_group_owner(group_id, auth.uid()::text)
);

create policy "group_members_delete_owner"
on public.group_members
for delete
to authenticated
using (
  public.is_group_owner(group_id, auth.uid()::text)
);

commit;
