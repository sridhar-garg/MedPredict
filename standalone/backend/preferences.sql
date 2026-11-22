-- Shared Aroham AI preferences on the existing Google-owned profile.
alter table public.mp_profiles
  add column if not exists language text not null default 'en'
  check (language in ('en','hi','bn','mr','ta','te','gu','kn','ml','pa','es','fr','de','pt','ar'));
