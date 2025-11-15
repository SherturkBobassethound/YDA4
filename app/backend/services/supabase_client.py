"""
Supabase client for database operations
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL must be set in .env file")

# Create Supabase client with service role key for admin operations
# Service role key bypasses RLS, but we'll still filter by user_id in our queries
if SUPABASE_SERVICE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
else:
    raise ValueError("SUPABASE_SERVICE_KEY must be set in .env file")

def get_user_supabase_client(access_token: str) -> Client:
    """
    Create a Supabase client with the user's JWT token.
    This client will respect RLS policies and auth.uid() will be set correctly.
    """
    if not SUPABASE_ANON_KEY:
        # Fallback to service key if anon key is not available
        # But this won't work with RLS, so we should log a warning
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("SUPABASE_ANON_KEY not set, using service key. RLS may not work correctly.")
        return supabase
    
    # Create client with anon key
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    
    # Set the access token using the postgrest client's auth method
    # This ensures RLS policies can access auth.uid() correctly
    # The postgrest client is what handles the database queries
    client.postgrest.auth(access_token)
    
    return client
