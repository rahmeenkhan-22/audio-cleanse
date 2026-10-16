-- Pre-processed public audio vault (read-only for app users)
create table if not exists public.vault_tracks (
    id            text primary key,
    title         text not null,
    creator       text,
    category      text not null check (category in ('nasheed','quran','dua','podcast','dhikr')),
    triggers      text[] not null default '{}',   -- e.g. {working_out,driving,sleeping}
    stages        smallint[] not null default '{2,3}',
    audio_url     text not null,                  -- Supabase Storage public URL
    duration_sec  integer,
    license_note  text,                           -- who granted permission / which license
    is_active     boolean not null default true,
    created_at    timestamptz not null default now()
);

create index if not exists idx_vault_category on public.vault_tracks (category) where is_active;

alter table public.vault_tracks enable row level security;

-- Anyone with the anon key can read; nobody can write from the app.
-- Add/edit rows in the Dashboard or with the service-role key.
create policy "vault: public read" on public.vault_tracks
    for select using (is_active);

-- Storage: create a PUBLIC bucket named "vault" and upload files there.
