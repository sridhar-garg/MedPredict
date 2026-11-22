begin;
-- Separate personal state for the approved integrated modules. This is a fresh
-- store, not a migration or copy of existing third-party accounts.
create table public.workspace_module_state (
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  app_id text not null check (app_id in ('healthara','namastey','kaamigo')),
  state jsonb not null default '{}'::jsonb check (jsonb_typeof(state)='object' and octet_length(state::text)<=262144),
  summary jsonb not null default '{}'::jsonb check (jsonb_typeof(summary)='object' and octet_length(summary::text)<=4096),
  updated_at timestamptz not null default now(),
  primary key(user_id,app_id)
);
alter table public.workspace_module_state enable row level security;
revoke all on public.workspace_module_state from public,anon,authenticated;
grant select,insert,update,delete on public.workspace_module_state to authenticated;
create policy workspace_google_only on public.workspace_module_state as restrictive for all to authenticated using (((select auth.jwt())->'app_metadata'->>'provider')='google') with check (((select auth.jwt())->'app_metadata'->>'provider')='google');
create policy workspace_own_state on public.workspace_module_state for all to authenticated using ((select auth.uid())=user_id) with check ((select auth.uid())=user_id);
-- New community posts are explicitly published in the combined edition.
create table public.workspace_kaamigo_listings (
  id uuid primary key default gen_random_uuid(),
  creator_uid uuid not null default auth.uid() references auth.users(id) on delete cascade,
  type text not null check(type in ('skill','job','space')),
  offer text not null check(char_length(offer) between 1 and 200),
  need text not null default '' check(char_length(need)<=1000),
  rate text not null default '' check(char_length(rate)<=40),
  status text not null default 'active' check(status in ('active','withdrawn')),
  created_at timestamptz not null default now()
);
alter table public.workspace_kaamigo_listings enable row level security;
revoke all on public.workspace_kaamigo_listings from public,anon,authenticated;
grant select,insert,delete on public.workspace_kaamigo_listings to authenticated;
grant update(status) on public.workspace_kaamigo_listings to authenticated;
create policy workspace_google_only on public.workspace_kaamigo_listings as restrictive for all to authenticated using (((select auth.jwt())->'app_metadata'->>'provider')='google') with check (((select auth.jwt())->'app_metadata'->>'provider')='google');
create policy workspace_community_read on public.workspace_kaamigo_listings for select to authenticated using (status='active' or creator_uid=(select auth.uid()));
create policy workspace_community_publish on public.workspace_kaamigo_listings for insert to authenticated with check (creator_uid=(select auth.uid()) and status='active');
create policy workspace_community_withdraw on public.workspace_kaamigo_listings for update to authenticated using (creator_uid=(select auth.uid())) with check (creator_uid=(select auth.uid()) and status='withdrawn');
create policy workspace_community_delete on public.workspace_kaamigo_listings for delete to authenticated using (creator_uid=(select auth.uid()));
create index workspace_kaamigo_owner_date on public.workspace_kaamigo_listings(creator_uid,created_at desc);
create index workspace_kaamigo_active_date on public.workspace_kaamigo_listings(created_at desc) where status='active';
commit;
