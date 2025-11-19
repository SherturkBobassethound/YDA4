# Testing Sources in Dev Mode

## The Issue (FIXED!)

The `dev.sh` script was **not passing Supabase credentials** to the backend and frontend, so sources couldn't be saved even though you had valid credentials in `.env`.

## What Was Fixed

Updated `dev.sh` to:
1. ✅ Load environment variables from `.env` file
2. ✅ Pass all Supabase credentials to backend
3. ✅ Pass Supabase URL and Anon Key to frontend

---

## How to Test

### Step 1: Verify Your .env File

Make sure `/home/user/YDA4/.env` has **real credentials** (not placeholders):

```bash
cat .env | grep SUPABASE_URL
```

Should show something like:
```
SUPABASE_URL=https://xxxxx.supabase.co
```

If it shows `your-supabase-url-here`, run the setup script:
```bash
bash setup_supabase_env.sh
```

### Step 2: Verify Supabase Connection

```bash
python3 test_supabase_connection.py
```

Expected output:
```
✅ SUPABASE_URL: https://...
✅ SUPABASE_ANON_KEY: eyJhbG...
✅ Connected to Supabase
✅ 'sources' table exists
```

### Step 3: Kill Any Existing Dev Processes

```bash
# Kill any running dev.sh processes
pkill -f "uvicorn main:app"
pkill -f "uvicorn ollama_service:app"
pkill -f "npm run dev"

# Or use the nuclear option
killall python3 node
```

### Step 4: Start Dev Mode

```bash
cd /home/user/YDA4
bash dev.sh
```

Watch for this new line:
```
✓ Environment variables loaded
```

This confirms the `.env` file was loaded successfully.

### Step 5: Verify Backend Has Credentials

Check the backend logs to see if Supabase credentials are present:

```bash
tail -f logs/backend.log
```

Or manually check if the backend can see them:
```bash
# In a new terminal
curl http://localhost:8000/health
```

### Step 6: Test Processing a Podcast

1. Open browser: http://localhost:5173
2. Log in to your account
3. Paste a YouTube or Apple Podcasts URL
4. Click "Process"

### Step 7: Watch the Backend Logs

In another terminal:
```bash
tail -f logs/backend.log | grep -i "source"
```

You should see:
```
INFO: Saved source to database: [Your Podcast Title]
```

If you see this warning instead:
```
WARNING: Could not save source to database: ...
```

That means Supabase credentials still aren't reaching the backend.

### Step 8: Verify Sources Appear

After processing completes:

**1. Check Sidebar**
- The source should appear in the left sidebar

**2. Check Supabase Table**
- Go to: https://app.supabase.com
- Table Editor → `sources` table
- You should see a new row

**3. Check API Endpoint**
```bash
# Get your auth token from browser DevTools:
# Application → Local Storage → sb-*-auth-token

curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  http://localhost:8000/sources
```

Should return:
```json
{
  "sources": [
    {
      "id": "...",
      "title": "Your Podcast Title",
      "url": "...",
      "type": "youtube"
    }
  ]
}
```

---

## Troubleshooting Dev Mode

### Sources Still Not Saving

**Check 1: Is .env loaded?**
```bash
# Look for this line in dev.sh output
✓ Environment variables loaded
```

If missing, check:
```bash
ls -la .env  # File exists?
cat .env | head -5  # Has real values?
```

**Check 2: Does backend see credentials?**
```bash
# Add a debug line to see what backend receives
tail -f logs/backend.log
```

Look for startup messages. If you see errors about Supabase connection, credentials aren't being passed.

**Check 3: Are there syntax errors in .env?**
```bash
# .env should NOT have spaces around =
# WRONG: SUPABASE_URL = https://...
# RIGHT: SUPABASE_URL=https://...

cat .env | grep "= "
```

If you see any matches, remove the spaces.

**Check 4: Restart dev.sh**
```bash
# Press Ctrl+C to stop current dev.sh
# Then start again
bash dev.sh
```

### Frontend Can't Authenticate

**Check frontend environment:**
```bash
tail -f logs/frontend.log
```

Look for errors about Supabase initialization.

**Verify frontend can see env vars:**

Open browser DevTools → Console and check:
```javascript
console.log(import.meta.env.VITE_SUPABASE_URL)
```

Should show your Supabase URL, not `undefined`.

### Backend Logs Show "Could not save source"

This means:
1. ✅ Backend is running
2. ✅ Podcast processed successfully
3. ❌ Supabase credentials are wrong or table doesn't exist

**Fix:**
```bash
# Re-run connection test
python3 test_supabase_connection.py

# If it fails, check credentials
cat .env | grep SUPABASE

# If table doesn't exist, run migration
# (See QUICK_START.md Step 3)
```

---

## Quick Verification Checklist

Before starting dev.sh, verify:

- [ ] `.env` file exists and has real credentials
- [ ] `python3 test_supabase_connection.py` passes ✅
- [ ] `sources` table exists in Supabase
- [ ] No other dev processes running (kill them first)

After starting dev.sh, verify:

- [ ] You see "✓ Environment variables loaded"
- [ ] All services start without errors
- [ ] Frontend accessible at http://localhost:5173
- [ ] Backend accessible at http://localhost:8000

After processing a podcast, verify:

- [ ] Backend logs show "Saved source to database"
- [ ] Source appears in left sidebar
- [ ] Row appears in Supabase `sources` table

If all checkboxes are ticked, it's working! 🎉

---

## Common Dev Mode Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| "Warning: .env file not found" | Missing .env | Create it: `bash setup_supabase_env.sh` |
| Backend can't save sources | Credentials not passed | Restart dev.sh after creating .env |
| Frontend can't auth | VITE vars not set | dev.sh now sets them automatically |
| "Could not save source" in logs | Invalid credentials or missing table | Run `python3 test_supabase_connection.py` |
| Sidebar empty | Frontend not fetching | Check browser console for errors |

---

## Success Indicators

When everything is working, you'll see:

**1. In dev.sh output:**
```
✓ Environment variables loaded
✓ All services started!
```

**2. In backend logs:**
```
INFO: Saved source to database: [Title]
```

**3. In browser:**
- Source appears in sidebar
- Can click × to delete
- Source removed from both sidebar and Supabase

**4. In Supabase:**
- `sources` table has rows
- Each row has your user_id
- Timestamps match when you processed content

---

## If It's Still Not Working

1. Run diagnostic:
   ```bash
   python3 test_supabase_connection.py > diagnostic.txt 2>&1
   ```

2. Check backend logs:
   ```bash
   cat logs/backend.log | grep -i error > errors.txt
   ```

3. Share both files for debugging

Happy testing! 🚀
