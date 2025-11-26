"""
User preferences service for managing user-specific settings.
Handles storage and retrieval of model preferences from Supabase.
"""

from typing import Optional, Dict
from supabase import Client
from .supabase_client import get_user_supabase_client

# Available models that users can select
AVAILABLE_MODELS = [
    "gemma3:1b",
    "gemma3:4b",
    "gemma3:12b",
    "gemma3:27b",
    "qwen3:1.7b",
    "qwen3:4b",
    "qwen3:8b",
    "qwen3:14b",
    "qwen3:30b",
    "llama3.2:1b",  # Legacy model
    "llama3.2:3b",  # Legacy model
    "llama3:8b",    # Legacy model
]

DEFAULT_MODEL = "gemma3:1b"


class UserPreferencesService:
    """Service for managing user preferences in Supabase."""

    @staticmethod
    def get_user_preferences(user_id: str, access_token: str) -> Dict[str, str]:
        """
        Get user preferences from Supabase.

        Args:
            user_id: The user's UUID
            access_token: The user's JWT access token

        Returns:
            Dictionary with user preferences. Creates default preferences if none exist.
        """
        client = get_user_supabase_client(access_token)

        # Try to fetch existing preferences
        response = client.table('user_preferences').select('*').eq('user_id', user_id).execute()

        if response.data and len(response.data) > 0:
            prefs = response.data[0]
            return {
                "preferred_model": prefs.get("preferred_model", DEFAULT_MODEL),
                "updated_at": prefs.get("updated_at")
            }
        else:
            # No preferences exist, create default
            default_prefs = {
                "user_id": user_id,
                "preferred_model": DEFAULT_MODEL
            }

            try:
                insert_response = client.table('user_preferences').insert(default_prefs).execute()
                if insert_response.data and len(insert_response.data) > 0:
                    return {
                        "preferred_model": insert_response.data[0].get("preferred_model", DEFAULT_MODEL),
                        "updated_at": insert_response.data[0].get("updated_at")
                    }
            except Exception as e:
                print(f"Failed to create default preferences: {e}")

            # Return default even if insert failed
            return {
                "preferred_model": DEFAULT_MODEL,
                "updated_at": None
            }

    @staticmethod
    def update_user_preferences(user_id: str, access_token: str, preferred_model: str) -> Dict[str, str]:
        """
        Update user preferences in Supabase.

        Args:
            user_id: The user's UUID
            access_token: The user's JWT access token
            preferred_model: The model name to set as preference

        Returns:
            Updated preferences dictionary

        Raises:
            ValueError: If the model is not in the available models list
        """
        # Validate model
        if preferred_model not in AVAILABLE_MODELS:
            raise ValueError(f"Invalid model '{preferred_model}'. Must be one of: {', '.join(AVAILABLE_MODELS)}")

        client = get_user_supabase_client(access_token)

        # Check if preferences exist
        check_response = client.table('user_preferences').select('user_id').eq('user_id', user_id).execute()

        if check_response.data and len(check_response.data) > 0:
            # Update existing preferences
            response = client.table('user_preferences').update({
                "preferred_model": preferred_model
            }).eq('user_id', user_id).execute()
        else:
            # Insert new preferences
            response = client.table('user_preferences').insert({
                "user_id": user_id,
                "preferred_model": preferred_model
            }).execute()

        if response.data and len(response.data) > 0:
            return {
                "preferred_model": response.data[0].get("preferred_model", preferred_model),
                "updated_at": response.data[0].get("updated_at")
            }

        # Fallback return
        return {
            "preferred_model": preferred_model,
            "updated_at": None
        }

    @staticmethod
    def is_valid_model(model: str) -> bool:
        """Check if a model name is in the available models list."""
        return model in AVAILABLE_MODELS
