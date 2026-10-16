import os
import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    """Initialize and cache the Supabase client connection."""
    # Reads from .streamlit/secrets.toml locally or Hugging Face Secrets when deployed
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

class DatabaseManager:
    def __init__(self):
        self.client = get_supabase_client()

    def get_cached_audio(self, file_hash: str):
        """Check if an audio file hash already exists in Supabase."""
        response = self.client.table("audio_cache").select("*").eq("file_hash", file_hash).execute()
        if response.data:
            return response.data[0]  # Return cached metadata/URL
        return None

    def save_audio_cache(self, file_hash: str, track_title: str, storage_url: str):
        """Save a newly processed track record to the cache table."""
        data = {
            "file_hash": file_hash,
            "track_title": track_title,
            "storage_url": storage_url
        }
        return self.client.table("audio_cache").insert(data).execute()

    def log_mood_craving(self, user_id: str, intensity: int, context: str, emotion: str):
        """Log a daily craving/mood record for user analytics."""
        data = {
            "user_id": user_id,
            "craving_intensity": intensity,
            "trigger_context": context,
            "emotional_state": emotion
        }
        return self.client.table("mood_analytics").insert(data).execute()