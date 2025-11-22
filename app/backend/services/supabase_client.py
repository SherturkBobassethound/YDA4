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
    import logging
    logger = logging.getLogger(__name__)

    if not SUPABASE_ANON_KEY:
        # If SUPABASE_ANON_KEY is not set, use service key but set the JWT token
        # This allows RLS policies to work with auth.uid()
        logger.warning("SUPABASE_ANON_KEY not set. Using service key with user JWT token.")
        client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        # Set the JWT token in the Authorization header for RLS to work
        client.postgrest.auth(access_token)
        return client

    # Create client with anon key (preferred method)
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

    # Set the access token using the postgrest client's auth method
    # This ensures RLS policies can access auth.uid() correctly
    # The postgrest client is what handles the database queries
    client.postgrest.auth(access_token)

    return client
