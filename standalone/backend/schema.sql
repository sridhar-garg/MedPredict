-- Standalone MedPredict: Google-only identity, owned records and explicit sharing.
-- Execute in a new, owner-approved Supabase project; never overwrite legacy data.
begin;
create table public.mp_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '' check (char_length(display_name)<=100),
  theme text not null default 'light' check(theme in ('light','dark')),
  created_at timestamptz not null default now()
);
create table public.mp_records (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  kind text not null check(kind in ('assessment','screening','report','assistant','accessibility','imaging')),
  title text not null check(char_length(title) between 1 and 160),
  payload jsonb not null check(jsonb_typeof(payload)='object' and octet_length(payload::text)<=32768),
  created_at timestamptz not null default now()
);
create index mp_records_owner_date_idx on public.mp_records(user_id, created_at desc);
create table public.mp_reviews (
  user_id uuid primary key references auth.users(id) on delete cascade default auth.uid(),
  display_name text not null check(char_length(display_name) between 1 and 80),
  rating smallint not null check(rating between 1 and 5),
  review text not null check(char_length(review) between 1 and 1000),
  consent boolean not null check(consent),
  created_at timestamptz not null default now()
);
create table public.mp_family_links (
  id uuid primary key default gen_random_uuid(),
  sender_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  recipient_id uuid not null references auth.users(id) on delete cascade,
  status text not null default 'pending' check(status in ('pending','accepted','declined')),
  created_at timestamptz not null default now(),
  check(sender_id<>recipient_id), unique(sender_id,recipient_id)
);
create index mp_family_recipient_idx on public.mp_family_links(recipient_id,status);
create index mp_family_sender_idx on public.mp_family_links(sender_id,status);
create table public.mp_shared_records (
  id uuid primary key default gen_random_uuid(),
  link_id uuid not null references public.mp_family_links(id) on delete cascade,
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  recipient_id uuid not null references auth.users(id) on delete cascade,
  record_id uuid not null references public.mp_records(id) on delete cascade,
  title text not null check(char_length(title) between 1 and 160),
  payload jsonb not null check(jsonb_typeof(payload)='object' and octet_length(payload::text)<=32768),
  shared_at timestamptz not null default now(),
  unique(record_id,recipient_id)
);
create index mp_shared_recipient_idx on public.mp_shared_records(recipient_id,shared_at desc);
create index mp_shared_owner_idx on public.mp_shared_records(owner_id,shared_at desc);
create index mp_shared_link_idx on public.mp_shared_records(link_id);

alter table public.mp_profiles enable row level security;
alter table public.mp_records enable row level security;
alter table public.mp_reviews enable row level security;
alter table public.mp_family_links enable row level security;
alter table public.mp_shared_records enable row level security;

revoke all on public.mp_profiles,public.mp_records,public.mp_reviews,public.mp_family_links,public.mp_shared_records from anon,authenticated;
grant select,insert,update,delete on public.mp_profiles,public.mp_records,public.mp_reviews to authenticated;
grant select,insert,delete on public.mp_family_links to authenticated;
grant update(status) on public.mp_family_links to authenticated;
grant select,insert,delete on public.mp_shared_records to authenticated;

-- Restrictive policy applies to every operation: a Supabase account created by
-- a different provider cannot use this Google-only app's data API.
create policy google_only on public.mp_profiles as restrictive for all to authenticated using (((select auth.jwt())->'app_metadata'->>'provider')='google') with check (((select auth.jwt())->'app_metadata'->>'provider')='google');
create policy google_only on public.mp_records as restrictive for all to authenticated using (((select auth.jwt())->'app_metadata'->>'provider')='google') with check (((select auth.jwt())->'app_metadata'->>'provider')='google');
create policy google_only on public.mp_reviews as restrictive for all to authenticated using (((select auth.jwt())->'app_metadata'->>'provider')='google') with check (((select auth.jwt())->'app_metadata'->>'provider')='google');
create policy google_only on public.mp_family_links as restrictive for all to authenticated using (((select auth.jwt())->'app_metadata'->>'provider')='google') with check (((select auth.jwt())->'app_metadata'->>'provider')='google');
create policy google_only on public.mp_shared_records as restrictive for all to authenticated using (((select auth.jwt())->'app_metadata'->>'provider')='google') with check (((select auth.jwt())->'app_metadata'->>'provider')='google');

create policy own_profile on public.mp_profiles for all to authenticated using ((select auth.uid())=user_id) with check ((select auth.uid())=user_id);
create policy own_records on public.mp_records for all to authenticated using ((select auth.uid())=user_id) with check ((select auth.uid())=user_id);
create policy view_consented_reviews on public.mp_reviews for select to authenticated using (consent);
create policy own_review on public.mp_reviews for all to authenticated using ((select auth.uid())=user_id) with check ((select auth.uid())=user_id and consent);
create policy family_participants_read on public.mp_family_links for select to authenticated using ((select auth.uid()) in (sender_id,recipient_id));
create policy family_sender_invites on public.mp_family_links for insert to authenticated with check ((select auth.uid())=sender_id and status='pending');
create policy family_recipient_responds on public.mp_family_links for update to authenticated using ((select auth.uid())=recipient_id and status='pending') with check ((select auth.uid())=recipient_id and status in ('accepted','declined'));
create policy family_participants_revoke on public.mp_family_links for delete to authenticated using ((select auth.uid()) in (sender_id,recipient_id));
create policy share_owner_read on public.mp_shared_records for select to authenticated using ((select auth.uid())=owner_id);
create policy shared_recipient_read on public.mp_shared_records for select to authenticated using (
  (select auth.uid())=recipient_id and exists(select 1 from public.mp_family_links l where l.id=mp_shared_records.link_id and l.status='accepted' and ((l.sender_id=mp_shared_records.owner_id and l.recipient_id=mp_shared_records.recipient_id) or (l.recipient_id=mp_shared_records.owner_id and l.sender_id=mp_shared_records.recipient_id)))
);
create policy share_owner_explicit on public.mp_shared_records for insert to authenticated with check (
  (select auth.uid())=owner_id and exists(select 1 from public.mp_records r where r.id=mp_shared_records.record_id and r.user_id=mp_shared_records.owner_id)
  and exists(select 1 from public.mp_family_links l where l.id=mp_shared_records.link_id and l.status='accepted' and ((l.sender_id=mp_shared_records.owner_id and l.recipient_id=mp_shared_records.recipient_id) or (l.recipient_id=mp_shared_records.owner_id and l.sender_id=mp_shared_records.recipient_id)))
);
create policy share_participants_revoke on public.mp_shared_records for delete to authenticated using ((select auth.uid()) in (owner_id,recipient_id));

create schema if not exists mp_private;
revoke all on schema mp_private from public,anon,authenticated;
grant usage on schema mp_private to service_role;
create table mp_private.ai_usage (scope text not null, day date not null, calls int not null check(calls>=0), primary key(scope,day));
alter table mp_private.ai_usage enable row level security;
grant select,insert,update on mp_private.ai_usage to service_role;
-- Invoker, service-role only. No SECURITY DEFINER or anonymous privileged RPC.
create function public.mp_claim_ai_call(p_user uuid) returns boolean language plpgsql security invoker set search_path='' as $$
declare claimed int;
begin
  if p_user is null then return false; end if;
  insert into mp_private.ai_usage(scope,day,calls) values ('user:'||p_user::text,current_date,1)
    on conflict(scope,day) do update set calls=mp_private.ai_usage.calls+1 where mp_private.ai_usage.calls<20 returning calls into claimed;
  if claimed is null then return false; end if;
  claimed:=null;
  insert into mp_private.ai_usage(scope,day,calls) values ('global',current_date,1)
    on conflict(scope,day) do update set calls=mp_private.ai_usage.calls+1 where mp_private.ai_usage.calls<300 returning calls into claimed;
  return claimed is not null;
end;
$$;
revoke execute on function public.mp_claim_ai_call(uuid) from public,anon,authenticated;
grant execute on function public.mp_claim_ai_call(uuid) to service_role;
commit;
