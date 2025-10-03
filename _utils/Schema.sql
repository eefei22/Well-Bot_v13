-- =============================================================================
-- Well-Bot · PostgreSQL Schema (MVP)
-- Supabase-friendly. Run as a privileged role (e.g., postgres / service role).
-- Timestamps in UTC. Uses gen_random_uuid() and pgvector.
-- =============================================================================

-- Extensions ------------------------------------------------------------------
create extension if not exists pgcrypto;           -- for gen_random_uuid()
create extension if not exists pg_trgm;            -- optional (fuzzy match support)
create extension if not exists vector;             -- pgvector

-- Types (Enums) ----------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_type where typname = 'todo_status_enum') then
    create type todo_status_enum as enum ('open','done');
  end if;

  if not exists (select 1 from pg_type where typname = 'meditation_outcome_enum') then
    create type meditation_outcome_enum as enum ('completed','canceled');
  end if;

  if not exists (select 1 from pg_type where typname = 'quote_category_enum') then
    create type quote_category_enum as enum ('islamic','buddhist','christian','hindu','general');
  end if;
end$$;

-- Constants -------------------------------------------------------------------
-- Embedding dimensions: all-MiniLM-L6-v2 and e5-small-v2 are both 384
-- Adjust if you ever swap to a different size.
create or replace function wb_embedding_dim() returns int language sql immutable as $$
  select 384;
$$;

-- Utility: updated_at trigger --------------------------------------------------
create or replace function wb_touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end$$;

-- =============================================================================
-- Core Content Tables
-- =============================================================================

-- Conversations & Messages ----------------------------------------------------
create table if not exists wb_conversation (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users(id) on delete cascade,
  started_at    timestamptz not null default now(),
  ended_at      timestamptz,
  reason_ended  text
);

create index if not exists wb_conversation_user_started_idx
  on wb_conversation (user_id, started_at desc);

create table if not exists wb_message (
  id               uuid primary key default gen_random_uuid(),
  conversation_id  uuid not null references wb_conversation(id) on delete cascade,
  role             text not null check (role in ('user','assistant')),
  text             text not null,
  created_at       timestamptz not null default now()
);

create index if not exists wb_message_conv_created_idx
  on wb_message (conversation_id, created_at);

-- Journals --------------------------------------------------------------------
create table if not exists wb_journal (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade,
  title      text not null,
  body       text not null,
  mood       int  not null check (mood between 1 and 5),
  topics     text[] not null default '{}',
  is_draft   boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists wb_journal_user_created_idx
  on wb_journal (user_id, created_at desc);

create trigger wb_journal_touch_upd
before update on wb_journal
for each row execute function wb_touch_updated_at();

-- Gratitude -------------------------------------------------------------------
create table if not exists wb_gratitude_item (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade,
  text       text not null,
  created_at timestamptz not null default now()
);
create index if not exists wb_gratitude_user_created_idx
  on wb_gratitude_item (user_id, created_at desc);

-- To-Do -----------------------------------------------------------------------
create table if not exists wb_todo_item (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users(id) on delete cascade,
  title         text not null,
  status        todo_status_enum not null default 'open',
  created_at    timestamptz not null default now(),
  completed_at  timestamptz
);
create index if not exists wb_todo_user_status_created_idx
  on wb_todo_item (user_id, status, created_at desc);
create index if not exists wb_todo_user_title_idx
  on wb_todo_item using gin ( (upper(title)) gin_trgm_ops );

-- Meditation ------------------------------------------------------------------
create table if not exists wb_meditation_video (
  id     uuid primary key default gen_random_uuid(),
  uri    text not null,
  label  text not null,
  active boolean not null default true
);
create index if not exists wb_meditation_video_active_idx
  on wb_meditation_video (active);

create table if not exists wb_meditation_log (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  video_id    uuid not null references wb_meditation_video(id) on delete set null,
  started_at  timestamptz not null,
  ended_at    timestamptz,
  outcome     meditation_outcome_enum not null,
  created_at  timestamptz not null default now()
);
create index if not exists wb_meditation_log_user_created_idx
  on wb_meditation_log (user_id, created_at desc);

-- Spiritual Quotes -------------------------------------------------------------
create table if not exists wb_quote (
  id        uuid primary key default gen_random_uuid(),
  category  quote_category_enum not null,
  text      text not null
);
create index if not exists wb_quote_category_idx
  on wb_quote (category);

create table if not exists wb_quote_seen (
  user_id   uuid not null references auth.users(id) on delete cascade,
  quote_id  uuid not null references wb_quote(id) on delete cascade,
  seen_at   timestamptz not null default now(),
  primary key (user_id, quote_id)
);
create index if not exists wb_quote_seen_user_seen_idx
  on wb_quote_seen (user_id, seen_at desc);

-- Preferences -----------------------------------------------------------------
create table if not exists wb_preferences (
  user_id   uuid primary key references auth.users(id) on delete cascade,
  language  text not null default 'en',
  religion  quote_category_enum,
  flags     jsonb not null default '{}'::jsonb
);

-- Activity Events --------------------------------------------------------------
create table if not exists wb_activity_event (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade,
  type       text not null check (type in ('journal','gratitude','todo','meditation','quote')),
  ref_id     uuid,
  action     text not null,
  created_at timestamptz not null default now()
);
create index if not exists wb_activity_event_user_created_idx
  on wb_activity_event (user_id, created_at desc);

-- Embeddings ------------------------------------------------------------------
create table if not exists wb_embeddings (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade,
  kind       text not null check (kind in ('message','journal','todo','preference','gratitude')),
  ref_id     uuid not null,
  vector     vector( (select wb_embedding_dim()) ) not null,
  model_tag  text not null check (model_tag in ('miniLM','e5')),
  created_at timestamptz not null default now()
);
create index if not exists wb_embeddings_user_kind_ref_idx
  on wb_embeddings (user_id, kind, ref_id);
-- Choose IVFFlat or HNSW depending on your pgvector build; Supabase supports ivfflat.
-- You must create the index after loading some data + running "analyze".
-- Example IVFFlat (lists=100):
-- create index wb_embeddings_vec_idx on wb_embeddings using ivfflat (vector vector_l2_ops) with (lists = 100);

-- Logs ------------------------------------------------------------------------
create table if not exists wb_session_log (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null references auth.users(id) on delete cascade,
  started_at       timestamptz not null default now(),
  ended_at         timestamptz,
  reason_ended     text check (reason_ended in ('manual','inactivity')),
  avg_latency_ms   integer,
  asr_wer_estimate numeric
);

create table if not exists wb_tool_invocation_log (
  id            uuid primary key default gen_random_uuid(),
  session_id    uuid,
  tool          text not null,
  status        text not null check (status in ('ok','error')),
  duration_ms   integer,
  error_code    text,
  payload_size  integer,
  created_at    timestamptz not null default now()
);

create table if not exists wb_safety_event (
  id                 uuid primary key default gen_random_uuid(),
  session_id         uuid,
  ts                 timestamptz not null default now(),
  lang               text,
  action_taken       text,
  user_acknowledged  boolean,
  redacted_phrase    text,
  severity           text check (severity in ('SI_INTENT','SI_IDEATION','SELF_HARM'))
);

-- =============================================================================
-- Row Level Security (RLS)
-- =============================================================================

-- Enable RLS on user-scoped tables
alter table wb_conversation          enable row level security;
alter table wb_message               enable row level security;
alter table wb_journal               enable row level security;
alter table wb_gratitude_item        enable row level security;
alter table wb_todo_item             enable row level security;
alter table wb_meditation_log        enable row level security;
alter table wb_quote_seen            enable row level security;
alter table wb_preferences           enable row level security;
alter table wb_activity_event        enable row level security;
alter table wb_embeddings            enable row level security;
alter table wb_session_log           enable row level security;
alter table wb_tool_invocation_log   enable row level security;
alter table wb_safety_event          enable row level security;

-- Read-only shared tables (videos, quotes) - readable by authenticated users
alter table wb_meditation_video      enable row level security;
alter table wb_quote                 enable row level security;

-- Policies: per-user ownership -----------------------------------------------
-- NOTE: Supabase uses auth.uid() in RLS policies.

-- Conversations
create policy wb_conversation_rw on wb_conversation
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Messages (via conversation ownership)
create policy wb_message_rw on wb_message
  for all using (
    exists (select 1 from wb_conversation c where c.id = conversation_id and c.user_id = auth.uid())
  ) with check (
    exists (select 1 from wb_conversation c where c.id = conversation_id and c.user_id = auth.uid())
  );

-- Journals
create policy wb_journal_rw on wb_journal
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Gratitude
create policy wb_gratitude_rw on wb_gratitude_item
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- To-Dos
create policy wb_todo_rw on wb_todo_item
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Meditation logs
create policy wb_meditation_log_rw on wb_meditation_log
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Quote seen
create policy wb_quote_seen_rw on wb_quote_seen
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Preferences
create policy wb_prefs_rw on wb_preferences
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Activity events
create policy wb_activity_event_rw on wb_activity_event
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Embeddings
create policy wb_embeddings_rw on wb_embeddings
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Session log (user can only read their own; writes typically via service role)
create policy wb_session_log_select on wb_session_log
  for select using (user_id = auth.uid());
create policy wb_session_log_insert on wb_session_log
  for insert with check (user_id = auth.uid());
create policy wb_session_log_update on wb_session_log
  for update using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Tool invocation log (allow read own; inserts generally via client)
create policy wb_tool_log_select on wb_tool_invocation_log
  for select using (true); -- or restrict per session if needed
create policy wb_tool_log_insert on wb_tool_invocation_log
  for insert with check (true);

-- Safety event (allow read own session if you store user link elsewhere; otherwise service-only)
create policy wb_safety_event_read_self on wb_safety_event
  for select using (true); -- tighten if needed
create policy wb_safety_event_insert on wb_safety_event
  for insert with check (true);

-- Shared reference tables: allow read for authenticated; write restricted to service role
create policy wb_meditation_video_read on wb_meditation_video
  for select using ( auth.role() = 'authenticated' );
create policy wb_quote_read on wb_quote
  for select using ( auth.role() = 'authenticated' );

-- =============================================================================
-- Seeds (optional, minimal)
-- =============================================================================

-- Meditation videos (3-minute variants; replace URIs with your Supabase Storage URLs)
insert into wb_meditation_video (id, uri, label, active) values
  (gen_random_uuid(), 'public/meditations/3min_variant_a.mp4', '3-min variant A', true),
  (gen_random_uuid(), 'public/meditations/3min_variant_b.mp4', '3-min variant B', true),
  (gen_random_uuid(), 'public/meditations/3min_variant_c.mp4', '3-min variant C', true)
on conflict do nothing;

-- Quotes (a few per category as placeholders; expand via CSV later)
insert into wb_quote (id, category, text) values
  (gen_random_uuid(), 'general',   'Breathe. You are stronger than you think.'),
  (gen_random_uuid(), 'general',   'Small steps still move you forward.'),
  (gen_random_uuid(), 'islamic',   'Indeed, with hardship [will be] ease.'),
  (gen_random_uuid(), 'buddhist',  'Peace comes from within. Do not seek it without.'),
  (gen_random_uuid(), 'christian', 'Let all that you do be done in love.'),
  (gen_random_uuid(), 'hindu',     'The soul is neither born, and nor does it die.')
on conflict do nothing;

-- =============================================================================
-- Notes
-- - Create the pgvector ANN index after initial load, tuned to your dataset size.
-- - Embedding creation is handled app-side; this schema only stores vectors.
-- - Consider vaulting service-level inserts (logs) using Supabase service key.
-- =============================================================================
