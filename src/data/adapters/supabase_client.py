"""
Supabase client configuration and utilities for AI Finance Platform.
"""

from typing import Optional
from supabase import Client, create_client
from core.config import settings


class SupabaseClient:
    """Singleton wrapper for Supabase client."""

    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Optional[Client]:
        """Get or create Supabase client instance."""
        if cls._instance is None:
            if settings.SUPABASE_URL and settings.SUPABASE_KEY:
                cls._instance = create_client(
                    settings.SUPABASE_URL, settings.SUPABASE_KEY
                )
        return cls._instance

    @classmethod
    def is_configured(cls) -> bool:
        """Check if Supabase is properly configured."""
        return bool(settings.SUPABASE_URL and settings.SUPABASE_KEY)

    @classmethod
    def reset(cls):
        """Reset client instance (useful for testing)."""
        cls._instance = None


def get_supabase_client() -> Optional[Client]:
    """Get Supabase client instance."""
    return SupabaseClient.get_client()


def get_supabase_table(table_name: str):
    """Get a table reference from Supabase."""
    client = get_supabase_client()
    if client is None:
        return None
    return client.table(table_name)
