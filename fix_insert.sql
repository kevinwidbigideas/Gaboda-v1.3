begin;

drop policy if exists "group_members_insert_owner" on public.group_members;
create policy "group_members_insert_owner"
on public.group_members
for insert
with check (
  true
);

commit;
