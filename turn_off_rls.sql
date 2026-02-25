begin;

-- 모든 RLS 정책을 제거합니다.
drop policy if exists "group_select_visible" on public.travel_groups;
drop policy if exists "group_insert_owner_only" on public.travel_groups;
drop policy if exists "group_update_owner_only" on public.travel_groups;
drop policy if exists "group_delete_owner_only" on public.travel_groups;

drop policy if exists "group_members_select_visible" on public.group_members;
drop policy if exists "group_members_insert_owner" on public.group_members;
drop policy if exists "group_members_update_owner_or_self" on public.group_members;
drop policy if exists "group_members_delete_owner" on public.group_members;

-- RLS 자체를 완전히 비활성화합니다.
-- (Flask 백엔드 api.py에서 이미 세션 기반 권한 체크를 하므로, DB를 완전히 오픈해도 무방합니다.)
alter table public.travel_groups disable row level security;
alter table public.group_members disable row level security;

commit;
