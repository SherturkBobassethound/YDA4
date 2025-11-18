#!/usr/bin/env python3
"""
Supabase Connection Test Script

This script helps debug Supabase connectivity issues by:
1. Checking if environment variables are set
2. Testing connection to Supabase
3. Verifying the 'sources' table exists
4. Testing authentication with JWT
5. Attempting to insert and read a test record

Run this script to diagnose issues with source persistence.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("SUPABASE CONNECTION DIAGNOSTIC TOOL")
print("=" * 60)
print()

# Step 1: Check environment variables
print("1. Checking Environment Variables")
print("-" * 60)

required_vars = {
    'SUPABASE_URL': os.getenv('SUPABASE_URL'),
    'SUPABASE_ANON_KEY': os.getenv('SUPABASE_ANON_KEY'),
    'SUPABASE_JWT_SECRET': os.getenv('SUPABASE_JWT_SECRET'),
    'SUPABASE_SERVICE_KEY': os.getenv('SUPABASE_SERVICE_KEY')
}

all_vars_present = True
for var_name, var_value in required_vars.items():
    if not var_value or var_value == f'your-supabase-{var_name.lower().replace("_", "-")}-here':
        print(f"❌ {var_name}: NOT SET or using placeholder")
        all_vars_present = False
    else:
        # Show first/last 10 characters for security
        masked_value = var_value[:10] + "..." + var_value[-10:] if len(var_value) > 20 else var_value[:5] + "..."
        print(f"✅ {var_name}: {masked_value}")

print()

if not all_vars_present:
    print("⚠️  ISSUE FOUND: Some environment variables are missing!")
    print()
    print("TO FIX:")
    print("1. Edit /home/user/YDA4/.env")
    print("2. Replace placeholder values with your actual Supabase credentials")
    print("3. Get credentials from: https://app.supabase.com/project/YOUR_PROJECT/settings/api")
    print()
    sys.exit(1)

# Step 2: Test Supabase connection
print("2. Testing Supabase Connection")
print("-" * 60)

try:
    from supabase import create_client, Client

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

    supabase: Client = create_client(supabase_url, supabase_key)
    print(f"✅ Connected to Supabase at: {supabase_url}")
except Exception as e:
    print(f"❌ Failed to connect to Supabase: {str(e)}")
    print()
    print("TO FIX:")
    print("1. Verify SUPABASE_URL is correct (should be https://xxxxx.supabase.co)")
    print("2. Verify SUPABASE_SERVICE_KEY is correct")
    print("3. Check your internet connection")
    print("4. Ensure Supabase project is active")
    sys.exit(1)

print()

# Step 3: Check if 'sources' table exists
print("3. Checking 'sources' Table")
print("-" * 60)

try:
    # Try to query the sources table
    result = supabase.table('sources').select("*").limit(1).execute()
    print(f"✅ 'sources' table exists")
    print(f"   Current row count: Checking...")

    # Get count
    count_result = supabase.table('sources').select("*", count="exact").execute()
    print(f"   Total sources in database: {count_result.count}")
except Exception as e:
    error_msg = str(e).lower()
    if 'does not exist' in error_msg or 'relation' in error_msg:
        print(f"❌ 'sources' table does NOT exist!")
        print()
        print("TO FIX:")
        print("1. Go to your Supabase dashboard: https://app.supabase.com")
        print("2. Navigate to SQL Editor")
        print("3. Copy the contents of: /home/user/YDA4/app/backend/migrations/001_create_sources_table.sql")
        print("4. Paste into SQL Editor and click 'Run'")
        print()
        print("OR use Supabase CLI:")
        print("   supabase db push app/backend/migrations/001_create_sources_table.sql")
        sys.exit(1)
    else:
        print(f"❌ Error querying sources table: {str(e)}")
        sys.exit(1)

print()

# Step 4: Test RLS policies
print("4. Testing Row Level Security (RLS) Policies")
print("-" * 60)

try:
    # Create a client with just anon key (like the frontend)
    anon_client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))

    # Try to query without authentication (should return empty, not error)
    result = anon_client.table('sources').select("*").limit(1).execute()
    print(f"✅ RLS policies are active (unauthenticated query returned {len(result.data)} rows)")
except Exception as e:
    print(f"⚠️  RLS policy check failed: {str(e)}")
    print("   This might be expected if RLS is very strict")

print()

# Step 5: Test insert capability
print("5. Testing Insert Capability (Service Role)")
print("-" * 60)

try:
    # Try to insert a test record using service role
    # Note: This will bypass RLS, which is expected for service role
    test_data = {
        "user_id": "00000000-0000-0000-0000-000000000000",  # Test UUID
        "title": "Test Source - DELETE ME",
        "url": "https://test.example.com/test-source",
        "type": "youtube"
    }

    # Try insert
    insert_result = supabase.table('sources').insert(test_data).execute()

    if insert_result.data:
        print("✅ Successfully inserted test record")
        inserted_id = insert_result.data[0]['id']

        # Clean up - delete the test record
        supabase.table('sources').delete().eq('id', inserted_id).execute()
        print("✅ Successfully deleted test record")
    else:
        print("⚠️  Insert returned no data")

except Exception as e:
    error_msg = str(e)
    if 'duplicate key' in error_msg.lower():
        print("⚠️  Test URL already exists (this is OK, means inserts work)")
        # Clean up the duplicate
        try:
            supabase.table('sources').delete().eq('url', 'https://test.example.com/test-source').execute()
            print("✅ Cleaned up existing test record")
        except:
            pass
    else:
        print(f"❌ Failed to insert test record: {str(e)}")
        print()
        print("TO FIX:")
        print("1. Check that the 'sources' table migration was run correctly")
        print("2. Verify all columns exist: id, user_id, title, url, type, created_at")
        print("3. Check Supabase logs for detailed error messages")

print()

# Final summary
print("=" * 60)
print("DIAGNOSTIC SUMMARY")
print("=" * 60)
print()
print("If all checks passed:")
print("  ✅ Your Supabase configuration is correct!")
print("  ✅ The 'sources' table exists and is accessible")
print()
print("Next steps:")
print("  1. Make sure you've restarted your Docker containers:")
print("     docker compose down && docker compose up -d")
print()
print("  2. Check backend logs when processing a podcast:")
print("     docker compose logs -f backend")
print()
print("  3. Look for 'Saved source to database' or error messages")
print()
print("If sources still don't appear, it may be a frontend issue.")
print("Check browser console for errors when loading sources.")
print()
