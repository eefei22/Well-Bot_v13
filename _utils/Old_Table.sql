-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.conversations (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  owner_id uuid NOT NULL,
  title text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  archived boolean NOT NULL DEFAULT false,
  user_id uuid,
  CONSTRAINT conversations_pkey PRIMARY KEY (id),
  CONSTRAINT conversations_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES auth.users(id),
  CONSTRAINT conversations_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id)
);
CREATE TABLE public.devices (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  serial_number text NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'inactive'::text CHECK (status = ANY (ARRAY['active'::text, 'inactive'::text])),
  fitbit_access_token text NOT NULL,
  fitbit_refresh_token text NOT NULL,
  fitbit_expires_at timestamp without time zone NOT NULL,
  CONSTRAINT devices_pkey PRIMARY KEY (id)
);
CREATE TABLE public.gratitude_list (
  id integer NOT NULL DEFAULT nextval('gratitude_list_id_seq'::regclass),
  item character varying NOT NULL,
  date_created date NOT NULL,
  user_id uuid NOT NULL,
  CONSTRAINT gratitude_list_pkey PRIMARY KEY (id)
);
CREATE TABLE public.guardians (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  email text NOT NULL UNIQUE,
  password text NOT NULL,
  fullname text,
  username text NOT NULL,
  verified boolean DEFAULT false,
  verification_token text,
  token_expires timestamp without time zone,
  token_email text,
  CONSTRAINT guardians_pkey PRIMARY KEY (id)
);
CREATE TABLE public.journals (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  title text NOT NULL,
  content text NOT NULL,
  mood text,
  tags ARRAY,
  is_private boolean NOT NULL DEFAULT true,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  session_conversation_id uuid,
  word_count integer DEFAULT 0,
  session_duration_minutes integer,
  CONSTRAINT journals_pkey PRIMARY KEY (id),
  CONSTRAINT journals_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id)
);
CREATE TABLE public.messages (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL,
  author_id uuid,
  role text NOT NULL CHECK (role = ANY (ARRAY['user'::text, 'assistant'::text, 'system'::text])),
  content text NOT NULL,
  token_count integer,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT messages_pkey PRIMARY KEY (id),
  CONSTRAINT messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id),
  CONSTRAINT messages_author_id_fkey FOREIGN KEY (author_id) REFERENCES auth.users(id)
);
CREATE TABLE public.permissions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  guardian_id uuid,
  user_id uuid,
  status text CHECK (status = ANY (ARRAY['active'::text, 'pending'::text, 'reject'::text, 'revoked'::text])),
  requested_at timestamp without time zone,
  updated_at timestamp without time zone,
  request_message text,
  CONSTRAINT permissions_pkey PRIMARY KEY (id),
  CONSTRAINT permissions_guardian_id_fkey FOREIGN KEY (guardian_id) REFERENCES public.guardians(id),
  CONSTRAINT permissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.quotes (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  text text NOT NULL,
  emotion text NOT NULL CHECK (emotion = ANY (ARRAY['happy'::text, 'sad'::text, 'angry'::text, 'fearful'::text])),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT quotes_pkey PRIMARY KEY (id)
);
CREATE TABLE public.todo_items (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  todo_list_id uuid NOT NULL,
  content text NOT NULL,
  position integer NOT NULL,
  completed boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT todo_items_pkey PRIMARY KEY (id),
  CONSTRAINT todo_items_todo_list_id_fkey FOREIGN KEY (todo_list_id) REFERENCES public.todo_lists(id)
);
CREATE TABLE public.todo_lists (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  title character varying NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT todo_lists_pkey PRIMARY KEY (id)
);
CREATE TABLE public.user_preferences (
  user_id uuid NOT NULL,
  preference_key text NOT NULL,
  preference_value text,
  CONSTRAINT user_preferences_pkey PRIMARY KEY (user_id, preference_key),
  CONSTRAINT user_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id)
);
CREATE TABLE public.users (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  email text NOT NULL UNIQUE,
  password text NOT NULL,
  fullname text NOT NULL,
  username text NOT NULL,
  gender text NOT NULL CHECK (gender = ANY (ARRAY['male'::text, 'female'::text, 'other'::text])),
  age integer NOT NULL CHECK (age >= 0),
  language text NOT NULL,
  cultural_background text NOT NULL,
  spiritual_beliefs text NOT NULL,
  device_id uuid,
  allow_guardian boolean DEFAULT false,
  verified boolean DEFAULT false,
  verification_token text,
  token_expires timestamp without time zone,
  token_email text,
  CONSTRAINT users_pkey PRIMARY KEY (id),
  CONSTRAINT users_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id)
);