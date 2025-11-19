# Supabase Setup Guide

This guide explains how to set up Supabase for the YODA application.

## Prerequisites

1. A Supabase account (https://supabase.com/)
2. A Supabase project created

## Environment Variables

Copy `.env.example` to `.env` and fill in your Supabase credentials:

```bash
# Get these from: https://app.supabase.com/project/YOUR_PROJECT/settings/api

SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_JWT_SECRET=your-jwt-secret-here  # Found in Project Settings > API > JWT Settings
SUPABASE_SERVICE_KEY=your-service-role-key-here

# Frontend variables (automatically use the values above)
VITE_SUPABASE_URL=${SUPABASE_URL}
VITE_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
```

## Database Migrations

### Running Migrations

You need to run the SQL migrations to create the necessary tables in your Supabase database.

**Option 1: Using Supabase Dashboard (Recommended)**

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor** in the left sidebar
3. Open the file `app/backend/migrations/001_create_sources_table.sql`
4. Copy the entire contents
5. Paste into the SQL Editor
6. Click **Run** to execute the migration

**Option 2: Using Supabase CLI**

If you have the Supabase CLI installed:

```bash
supabase db push app/backend/migrations/001_create_sources_table.sql
```

### What the Migration Creates

The migration creates:

- **`sources` table**: Stores user's processed podcast/YouTube sources
  - `id`: UUID primary key
  - `user_id`: References authenticated user (with CASCADE delete)
  - `title`: Source title (e.g., "Podcast Name: Episode Title")
  - `url`: Original URL
  - `type`: Either 'youtube' or 'podcast'
  - `created_at`: Timestamp

- **Row Level Security (RLS) policies**:
  - Users can only view their own sources
  - Users can only insert sources for themselves
  - Users can only delete their own sources

- **Indexes** for performance:
  - Index on `user_id` for fast user queries
  - Index on `created_at` for chronological ordering

## Verifying Setup

After running the migration, you can verify it worked:

1. In Supabase Dashboard, go to **Table Editor**
2. You should see a `sources` table
3. Check the **Policies** tab to ensure RLS policies are enabled

## How Sources Work

1. **Processing**: When a user processes a podcast/YouTube URL:
   - Audio is transcribed
   - Content is embedded into user-specific Qdrant vector database
   - Source metadata is saved to Supabase `sources` table

2. **Display**: Sources appear in the left sidebar
   - Fetched from `/sources` API endpoint
   - Filtered by authenticated user's ID
   - Displayed in chronological order (newest first)

3. **Deletion**: When a user deletes a source:
   - Vectors are removed from Qdrant vector database
   - Source metadata is deleted from Supabase
   - Source disappears from sidebar

## Troubleshooting

### Sources not appearing in sidebar

1. **Check authentication**: Make sure you're logged in
2. **Verify migration ran**: Check Supabase dashboard for `sources` table
3. **Check RLS policies**: Ensure policies are enabled in Supabase
4. **Check browser console**: Look for API errors
5. **Verify environment variables**: Ensure all Supabase vars are set correctly

### "Could not save source to database" warning

This error appears in backend logs when:
- Supabase credentials are incorrect
- The `sources` table doesn't exist (run migration!)
- RLS policies are blocking the insert
- Duplicate URL for the same user (intentional, to prevent duplicates)

### Sources saved but not displaying

Check browser console for errors when calling `/sources` endpoint. Common issues:
- JWT token expired (refresh browser)
- RLS policies too restrictive
- Frontend not authenticated properly
