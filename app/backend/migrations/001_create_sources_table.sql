-- Create sources table for storing user's processed content
CREATE TABLE IF NOT EXISTS sources (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('youtube', 'podcast')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure unique URL per user
    UNIQUE(user_id, url)
);

-- Create index for faster queries by user_id
CREATE INDEX IF NOT EXISTS idx_sources_user_id ON sources(user_id);

-- Create index for faster queries by created_at (for ordering)
CREATE INDEX IF NOT EXISTS idx_sources_created_at ON sources(created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE sources ENABLE ROW LEVEL SECURITY;

-- Create policy: Users can only see their own sources
CREATE POLICY "Users can view their own sources"
    ON sources FOR SELECT
    USING (auth.uid() = user_id);

-- Create policy: Users can insert their own sources
CREATE POLICY "Users can insert their own sources"
    ON sources FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Create policy: Users can delete their own sources
CREATE POLICY "Users can delete their own sources"
    ON sources FOR DELETE
    USING (auth.uid() = user_id);
