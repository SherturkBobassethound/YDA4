# Quick Start Guide - Fix Sources Not Appearing

This guide will help you fix the issue where sources aren't being saved to Supabase.

## Problem

- Podcasts process successfully ✅
- Sources don't appear in sidebar ❌
- No data in Supabase `sources` table ❌

## Root Cause

The `.env` file with Supabase credentials is missing or incomplete.

---

## Step-by-Step Fix

### Step 1: Get Your Supabase Credentials

1. Go to https://app.supabase.com
2. Open your project (or create one if you don't have it)
3. Click **Project Settings** (gear icon in bottom left)
4. Go to **API** section
5. Copy these values:

   - **Project URL** → This is your `SUPABASE_URL`
   - **anon public** key → This is your `SUPABASE_ANON_KEY`
   - **service_role** key → This is your `SUPABASE_SERVICE_KEY`

6. For JWT Secret:
   - Still in Project Settings → **API**
   - Scroll down to **JWT Settings**
   - Copy **JWT Secret** → This is your `SUPABASE_JWT_SECRET`

### Step 2: Edit the .env File

I've created a template `.env` file for you at `/home/user/YDA4/.env`

Edit this file and replace the placeholder values:

```bash
# Edit the .env file
nano /home/user/YDA4/.env

# Or use your preferred editor
vim /home/user/YDA4/.env
```

**Replace these lines:**
```bash
SUPABASE_URL=your-supabase-url-here
SUPABASE_ANON_KEY=your-supabase-anon-key-here
SUPABASE_JWT_SECRET=your-supabase-jwt-secret-here
SUPABASE_SERVICE_KEY=your-supabase-service-key-here
```

**With your actual values:**
```bash
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_JWT_SECRET=your-super-secret-jwt-secret-never-share-this
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Save and close the file.

### Step 3: Run the Supabase Migration

The `sources` table needs to be created in your Supabase database.

**Option A: Using Supabase Dashboard (Recommended)**

1. Go to your Supabase project dashboard
2. Click **SQL Editor** in the left sidebar
3. Click **New Query**
4. Copy the entire contents of this file:
   ```
   /home/user/YDA4/app/backend/migrations/001_create_sources_table.sql
   ```
5. Paste into the SQL Editor
6. Click **Run** (or press Cmd/Ctrl + Enter)
7. You should see "Success. No rows returned"

**Option B: View the migration file**

```bash
cat /home/user/YDA4/app/backend/migrations/001_create_sources_table.sql
```

Then copy and paste into Supabase SQL Editor.

### Step 4: Test the Connection

Run the diagnostic script I created:

```bash
cd /home/user/YDA4
python3 test_supabase_connection.py
```

This will check:
- ✅ Environment variables are set
- ✅ Connection to Supabase works
- ✅ `sources` table exists
- ✅ Insert/delete operations work

**If all checks pass**, continue to Step 5.
**If any checks fail**, follow the instructions in the script output.

### Step 5: Restart Docker Containers

The containers need to be restarted to pick up the new environment variables:

```bash
cd /home/user/YDA4

# Stop all containers
docker compose down

# Start all containers with new environment variables
docker compose up -d

# Watch the logs (optional, press Ctrl+C to exit)
docker compose logs -f backend
```

### Step 6: Test Processing a Podcast

1. Open your YODA application in the browser
2. Log in (or create an account)
3. Paste a YouTube or Apple Podcasts URL
4. Click **Process**
5. Wait for processing to complete

**Check the backend logs:**
```bash
docker compose logs backend | grep -i "saved source"
```

You should see:
```
backend_api | INFO: Saved source to database: [Title of your podcast]
```

### Step 7: Verify Sources Appear

1. Check the sidebar - you should see the source listed
2. Check Supabase dashboard:
   - Go to **Table Editor**
   - Click on `sources` table
   - You should see a row with your processed podcast

---

## Troubleshooting

### Still not working?

**1. Check Backend Logs**
```bash
docker compose logs backend | tail -100
```

Look for errors like:
- "Could not save source to database"
- "Failed to connect to Supabase"
- Any error messages with "Supabase" or "sources"

**2. Check Frontend Console**

Open browser DevTools (F12) → Console tab
Look for:
- Errors when loading sources
- Failed API requests to `/sources`

**3. Verify Environment Variables in Container**

```bash
docker compose exec backend env | grep SUPABASE
```

Should show your Supabase credentials (not placeholders).

**4. Check if Sources Table Exists**

Go to Supabase Dashboard → Table Editor
You should see a `sources` table with these columns:
- id (uuid)
- user_id (uuid)
- title (text)
- url (text)
- type (text)
- created_at (timestamp)

### Common Issues

| Issue | Solution |
|-------|----------|
| "Table does not exist" | Run the migration (Step 3) |
| Backend can't connect to Supabase | Check SUPABASE_URL and SUPABASE_SERVICE_KEY |
| Frontend can't authenticate | Check VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY |
| "duplicate key" error | Source already exists, this is expected behavior |
| Sources don't load in sidebar | Check browser console for auth errors |

---

## Quick Reference

**Environment file location:**
```
/home/user/YDA4/.env
```

**Migration file location:**
```
/home/user/YDA4/app/backend/migrations/001_create_sources_table.sql
```

**Test script:**
```bash
python3 /home/user/YDA4/test_supabase_connection.py
```

**Restart containers:**
```bash
docker compose down && docker compose up -d
```

**View logs:**
```bash
docker compose logs -f backend
```

---

## Need More Help?

Run the diagnostic tool and share the output:
```bash
python3 test_supabase_connection.py > supabase_diagnostic.txt 2>&1
cat supabase_diagnostic.txt
```

This will help identify the exact issue.
