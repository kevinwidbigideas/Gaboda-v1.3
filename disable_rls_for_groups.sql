begin;

-- 그룹, 멤버 테이블에 대한 모든 RLS 정책을 일괄 삭제합니다.
drop policy if exists "group_select_visible" on public.travel_groups;
drop policy if exists "group_insert_owner_only" on public.travel_groups;
drop policy if exists "group_update_owner_only" on public.travel_groups;
drop policy if exists "group_delete_owner_only" on public.travel_groups;
drop policy if exists "group_all_auth" on public.travel_groups;

drop policy if exists "group_members_select_visible" on public.group_members;
drop policy if exists "group_members_insert_owner" on public.group_members;
drop policy if exists "group_members_update_owner_or_self" on public.group_members;
drop policy if exists "group_members_delete_owner" on public.group_members;
drop policy if exists "member_all_auth" on public.group_members;

-- RLS 자체를 비활성화 (권한 제어는 Python 백엔드 API에서 처리)
alter table public.travel_groups disable row level security;
alter table public.group_members disable row level security;

commit;
