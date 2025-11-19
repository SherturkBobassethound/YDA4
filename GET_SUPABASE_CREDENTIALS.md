# How to Get Your Supabase Credentials

## You Need Real Credentials!

Your `.env` file currently has **placeholder values** like:
```
SUPABASE_URL=your-supabase-url-here  ❌ NOT REAL
```

These need to be replaced with **actual values** from your Supabase project.

---

## Option 1: Use the Interactive Setup Script (Easiest)

Run this command and follow the prompts:

```bash
cd /home/user/YDA4
bash setup_supabase_env.sh
```

It will guide you step-by-step to enter each credential.

---

## Option 2: Manual Setup

### Step 1: Go to Supabase Dashboard

1. Open your browser: https://app.supabase.com
2. **Login** to your account
3. **Select your project** (or create a new one)

### Step 2: Open Project Settings

1. Click the **⚙️ gear icon** in the bottom left
2. Click **"Project Settings"**
3. Click **"API"** in the left sidebar

### Step 3: Copy Your Credentials

You'll see a page with your API credentials. Copy each one:

#### 🔹 Project URL
```
Location: Top of the page
Label: "Project URL"
Example: https://abcdefghijklmn.supabase.co

Copy this to: SUPABASE_URL
```

#### 🔹 Anon/Public Key
```
Location: "Project API keys" section
Label: "anon" "public"
Starts with: eyJ...

Copy this to: SUPABASE_ANON_KEY
```

#### 🔹 Service Role Key
```
Location: "Project API keys" section
Label: "service_role" "secret"
Click: "Reveal" button first, then "Copy"
Starts with: eyJ...

⚠️  KEEP THIS SECRET! Don't share it!

Copy this to: SUPABASE_SERVICE_KEY
```

#### 🔹 JWT Secret
```
Location: Scroll down to "JWT Settings" section
Label: "JWT Secret"
This is a long string (not a JWT token)

⚠️  This is DIFFERENT from the service_role key above!

Copy this to: SUPABASE_JWT_SECRET
```

### Step 4: Edit Your .env File

```bash
# Option A: Use nano
nano /home/user/YDA4/.env

# Option B: Use vim
vim /home/user/YDA4/.env

# Option C: Use any text editor
```

Replace the placeholder values with what you copied:

**BEFORE:**
```bash
SUPABASE_URL=your-supabase-url-here
SUPABASE_ANON_KEY=your-supabase-anon-key-here
SUPABASE_JWT_SECRET=your-supabase-jwt-secret-here
SUPABASE_SERVICE_KEY=your-supabase-service-key-here
```

**AFTER:**
```bash
SUPABASE_URL=https://abcdefghijklmn.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1uIiwicm9sZSI6ImFub24iLCJpYXQiOjE2ODk1MjcwMTUsImV4cCI6MjAwNTEwMzAxNX0.kCB1Y...
SUPABASE_JWT_SECRET=UJBqL4OhvKz2mFHVn6YgTxR8NsE3PcWdA7kXm9Qr5tZ0
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1uIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTY4OTUyNzAxNSwiZXhwIjoyMDA1MTAzMDE1fQ.XYZ789...
```

Save and close the file.

---

## Step 5: Verify Your Credentials

Run the test script to make sure everything is correct:

```bash
cd /home/user/YDA4
python3 test_supabase_connection.py
```

**Expected output:**
```
✅ SUPABASE_URL: https://ab...
✅ SUPABASE_ANON_KEY: eyJhbG...
✅ SUPABASE_JWT_SECRET: UJBqL...
✅ SUPABASE_SERVICE_KEY: eyJhbG...
✅ Connected to Supabase at: https://...
```

If you see ❌ errors, the credentials are wrong. Double-check them!

---

## Step 6: Create the Database Table

Go back to Supabase dashboard:

1. Click **"SQL Editor"** in the left sidebar
2. Click **"New Query"**
3. Copy the contents of this file:
   ```bash
   cat /home/user/YDA4/app/backend/migrations/001_create_sources_table.sql
   ```
4. Paste into the SQL Editor
5. Click **"Run"** (or press Cmd/Ctrl + Enter)

You should see: **"Success. No rows returned"**

Verify the table was created:
- Go to **"Table Editor"** in the left sidebar
- You should see a **`sources`** table

---

## Step 7: Restart Docker Containers

Your containers need to pick up the new environment variables:

```bash
cd /home/user/YDA4

# Stop all containers
docker compose down

# Start with new environment
docker compose up -d

# Watch the logs (optional)
docker compose logs -f backend
```

---

## Step 8: Test!

1. Open your YODA app
2. Log in
3. Process a podcast or YouTube URL
4. **Check the backend logs:**
   ```bash
   docker compose logs backend | grep -i "saved source"
   ```

You should see:
```
✅ backend_api | INFO: Saved source to database: [Your Podcast Title]
```

5. **Check Supabase:**
   - Go to Table Editor → `sources` table
   - You should see a new row!

6. **Check the sidebar:**
   - The source should appear in the left sidebar

---

## Common Mistakes

| ❌ Mistake | ✅ Fix |
|-----------|-------|
| Copied placeholder values | Copy from Supabase dashboard |
| Forgot to restart containers | Run `docker compose down && docker compose up -d` |
| Didn't run migration | Run SQL in Supabase SQL Editor |
| Used wrong JWT value | JWT Secret ≠ Service Role Key |
| Extra spaces in .env | Remove spaces around `=` |

---

## Still Having Issues?

1. **Verify .env file:**
   ```bash
   cat /home/user/YDA4/.env | grep SUPABASE_URL
   ```
   Should show a real URL, not "your-supabase-url-here"

2. **Check if containers see the variables:**
   ```bash
   docker compose exec backend env | grep SUPABASE_URL
   ```
   Should show your real URL

3. **Check backend logs for errors:**
   ```bash
   docker compose logs backend | grep -i error
   docker compose logs backend | grep -i supabase
   ```

---

## Quick Checklist

- [ ] I have a Supabase account at https://app.supabase.com
- [ ] I have a Supabase project created
- [ ] I copied all 4 credentials from Supabase dashboard
- [ ] I replaced placeholders in `/home/user/YDA4/.env`
- [ ] I ran `python3 test_supabase_connection.py` ✅
- [ ] I ran the migration SQL in Supabase SQL Editor
- [ ] I restarted Docker: `docker compose down && docker compose up -d`
- [ ] I tested processing a podcast

If all boxes are checked, sources should appear! 🎉
