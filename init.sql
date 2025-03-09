-- Enable Row Level Security
ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;

-- Create a table for users
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    full_name TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Enable RLS on users table
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Create a table for meetings
CREATE TABLE IF NOT EXISTS public.meetings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) NOT NULL,
    title TEXT NOT NULL,
    file_url TEXT NOT NULL,
    transcript_status TEXT DEFAULT 'pending',
    transcript_text TEXT,
    duration_seconds INTEGER,
    speakers_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Enable RLS on meetings table
ALTER TABLE public.meetings ENABLE ROW LEVEL SECURITY;

-- Create policies
DROP POLICY IF EXISTS "Users can read their own data" ON public.users;
DROP POLICY IF EXISTS "Users can insert their own data" ON public.users;
DROP POLICY IF EXISTS "Users can read their own meetings" ON public.meetings;
DROP POLICY IF EXISTS "Users can insert their own meetings" ON public.meetings;

-- Allow anyone to register (insert) into users table
CREATE POLICY "Enable registration" ON public.users
    FOR INSERT
    WITH CHECK (true);

-- Users can only read their own data
CREATE POLICY "Users can read their own data" ON public.users
    FOR SELECT
    USING (auth.uid() = id);

-- Users can read their own meetings
CREATE POLICY "Users can read their own meetings" ON public.meetings
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own meetings
CREATE POLICY "Users can insert their own meetings" ON public.meetings
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Enable RLS
ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;
ALTER TABLE storage.buckets ENABLE ROW LEVEL SECURITY;
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Create policies for meetings
CREATE POLICY "Users can view their own meetings" ON meetings
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own meetings" ON meetings
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own meetings" ON meetings
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own meetings" ON meetings
    FOR DELETE USING (auth.uid() = user_id);

-- Create policies for storage buckets
CREATE POLICY "Enable read access for authenticated users" ON storage.buckets
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Enable insert access for authenticated users" ON storage.buckets
    FOR INSERT TO authenticated WITH CHECK (true);

-- Create policies for storage objects
CREATE POLICY "Users can upload objects" ON storage.objects
    FOR INSERT TO authenticated WITH CHECK (bucket_id = 'audio');

CREATE POLICY "Users can update their own objects" ON storage.objects
    FOR UPDATE TO authenticated USING (auth.uid()::text = owner);

CREATE POLICY "Users can delete their own objects" ON storage.objects
    FOR DELETE TO authenticated USING (auth.uid()::text = owner);

CREATE POLICY "Users can view their own objects" ON storage.objects
    FOR SELECT TO authenticated USING (auth.uid()::text = owner);

-- Create storage bucket
insert into storage.buckets (id, name, public)
values ('audio', 'audio', false);

-- Storage policies
CREATE POLICY "Allow authenticated uploads"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'audio' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Allow authenticated downloads"
ON storage.objects
FOR SELECT
TO authenticated
USING (
    bucket_id = 'audio' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Allow authenticated deletes"
ON storage.objects
FOR DELETE
TO authenticated
USING (
    bucket_id = 'audio' AND
    (storage.foldername(name))[1] = auth.uid()::text
);
