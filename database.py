"""
database.py: Supabase client initialization and resilience wrapper for Audio Cleanse.
"""
import logging
from typing import Optional
import streamlit as st
from supabase import Client, create_client

log = logging.getLogger(__name__)


class DatabaseManager:
    """Manages Supabase connection, mood logs, and audio cache handling."""

    def __init__(self):
        self.client: Optional[Client] = None
        self._init_client()

    def _init_client(self):
        """Safely initialize the Supabase client using Streamlit secrets."""
        try:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            self.client = create_client(url, key)
        except Exception as e:
            log.error(f"Failed to initialize Supabase client: {e}")
            self.client = None

    @property
    def is_connected(self) -> bool:
        """Returns True if the client is initialized."""
        return self.client is not None

    def log_mood(
        self,
        craving_score: int,
        trigger_context: str,
        emotional_state: str,
        day_number: int = 1,
        user_id: str = "00000000-0000-0000-0000-000000000000",
    ) -> bool:
        """Log user craving and emotional state safely into public.mood_logs."""
        if not self.is_connected:
            return False

        try:
            payload = {
                "user_id": user_id,
                "day_number": day_number,
                "craving_score": craving_score,
                "trigger_context": trigger_context,
                "emotional_state": emotional_state,
            }
            self.client.table("mood_logs").insert(payload).execute()
            return True
        except Exception as e:
            log.exception(f"Failed to log mood entry: {e}")
            return False

    def fetch_mood_logs(
        self, user_id: str = "00000000-0000-0000-0000-000000000000"
    ) -> list[dict]:
        """Fetch user logs safely with exception fallback."""
        if not self.is_connected:
            return []

        try:
            response = (
                self.client.table("mood_logs")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at")
                .execute()
            )
            return response.data or []
        except Exception as e:
            log.exception(f"Failed to fetch mood logs: {e}")
            return []

    def get_cached_audio(self, file_hash: str) -> Optional[dict]:
        """Retrieve existing processed track record from Supabase audio_cache table."""
        if not self.is_connected:
            return None
        try:
            res = (
                self.client.table("audio_cache")
                .select("*")
                .eq("file_hash", file_hash)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as e:
            log.exception(f"Failed to fetch cached audio: {e}")
            return None

    def save_audio_cache(
        self, file_hash: str, track_title: str, storage_url: str
    ) -> bool:
        """Save processed track details into public.audio_cache."""
        if not self.is_connected:
            return False
        try:
            payload = {
                "file_hash": file_hash,
                "track_title": track_title,
                "storage_url": storage_url,
            }
            self.client.table("audio_cache").insert(payload).execute()
            return True
        except Exception as e:
            log.exception(f"Failed to save audio cache: {e}")
            return False


@st.cache_resource(show_spinner=False)
def get_db() -> DatabaseManager:
    """Cached singleton instance of DatabaseManager."""
    return DatabaseManager()