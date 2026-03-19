-- Database setup for pre-registrations
-- Run this in the Supabase SQL Editor

-- 1) Create the pre_registrations table
create table if not exists public.pre_registrations (
    id uuid primary key default gen_random_uuid(),
    email text not null unique,
    created_at timestamptz not null default now()
);

-- 2) Enable Row Level Security (RLS)
alter table public.pre_registrations enable row level security;

-- 3) Allow public (anon/authenticated) to insert emails (pre-register)
drop policy if exists "allow_anon_insert_pre_reg" on public.pre_registrations;
create policy "allow_anon_insert_pre_reg"
on public.pre_registrations
for insert
to anon, authenticated
with check (true);

-- 4) (Optional) Allow service role or authenticated staff to read (if needed)
-- By default, no one can read these emails via public API unless specified.
