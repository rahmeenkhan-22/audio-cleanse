"""
app.py: Main entry point for the Audio Cleanse Streamlit application.
"""
import time
import pandas as pd
import static_ffmpeg
static_ffmpeg.add_paths(weak=True)
import streamlit as st
from auth import render_auth_gate, save_mood, load_moods
import analytics
from audio_processor import AudioProcessor
from database import DatabaseManager
import ui_components
from ui_components import pause_and_reflect, render_mixer, reset_pause
import vault
import stage3

# --- Page Configuration ---
st.set_page_config(
    page_title="Audio Cleanse",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Login gate: nothing below runs unless the user is signed in ---
if not render_auth_gate():
    st.stop()

# --- Database & Service Initialization ---
db = DatabaseManager()
processor = AudioProcessor()


class _UserDB:
    """Wraps the shared DB so analytics only ever sees the logged-in user's own entries."""

    def fetch_mood_logs(self, *args, **kwargs):
        return load_moods()

    def __getattr__(self, name):
        return getattr(db, name)


# --- SIDEBAR: User Controls & Mood Log ---
st.sidebar.title("⚙️ User Controls")

# Journey Day Simulation
journey_day = st.sidebar.slider(
    "Simulate Journey Day", min_value=1, max_value=40, value=1
)

st.sidebar.divider()

st.sidebar.header("📝 Daily Craving & Mood Log")

# Logging inputs
craving = st.sidebar.slider(
    "Music Craving Intensity (1-10)", min_value=1, max_value=10, value=5
)

context = st.sidebar.selectbox(
    "Trigger Context",
    [
        "Driving",
        "Working out",
        "Relaxing / Sleeping",
        "Boredom",
        "Stress",
        "Socializing",
    ],
)

emotion = st.sidebar.selectbox(
    "Emotional State", ["Anxious", "Tired", "Energetic", "Sad", "Stressed", "Calm"]
)

if st.sidebar.button("Log Entry"):
    success = save_mood(
        craving_score=craving,
        trigger_context=context,
        emotional_state=emotion,
        day_number=journey_day,
    )
    if success:
        st.sidebar.success("Mood log saved!")
        st.rerun()
    else:
        st.sidebar.error("Failed to save log. Please try again.")

# --- MAIN APP UI ---
st.title("🛡️ Audio Cleanse")
st.caption("A guided journey to transition away from instrumental music.")

# Current Status Headers
col_day, col_stage, col_status = st.columns(3)

# Calculate Stage based on Journey Day
if journey_day <= 10:
    stage_num = 1
    stage_status = "Active"
elif journey_day <= 25:
    stage_num = 2
    stage_status = "Transitioning"
else:
    stage_num = 3
    stage_status = "Pure Dhikr"

col_day.metric("Journey Day", f"Day {journey_day}")
col_stage.metric("Current Stage", f"Stage {stage_num}")
col_status.metric("Status", stage_status)

st.progress(min(journey_day / 40.0, 1.0))

# --- APP TABS ---
tabs = st.tabs(
    ["🎵 Audio Cleanse Engine", "🎧 Replacing the Trigger", "📊 Mood Analytics", "🌙 Quran & Dhikr"]
)

# TAB 1: Cleanse Engine & Mixer
with tabs[0]:
    st.subheader("🎵 Audio Cleanse Processing Engine")

    # Mode Selector
    engine_mode = st.radio(
        "Choose Operation Mode:",
        ["🎼 Convert / Remove Instrumental Music", "🎛️ Ambient Soundscape Mixer"],
        horizontal=True,
    )

    st.divider()

    if engine_mode == "🎼 Convert / Remove Instrumental Music":
        # --- Stage gate: S1 free, S2 needs Pause & Reflect, S3 locked ---
        if stage_num == 1:
            allowed = True
        elif stage_num == 2:
            st.warning(
                "Stage 2: conversion is throttled. Take a moment to reflect before processing new audio."
            )
            allowed = pause_and_reflect()
        else:
            allowed = False
            st.error(
                "🔒 The audio converter is locked in Stage 3. Open the '🌙 Quran & Dhikr' tab instead."
            )

        if allowed:
            st.markdown("### Remove or Filter Instrumental Music")
            st.caption(
                "Submit an audio link or file to apply stage-based frequency dampening."
            )

            input_type = st.radio(
                "Source Type:", ["Direct Audio URL", "Upload Audio File"], horizontal=True
            )

            if input_type == "Direct Audio URL":
                song_url = st.text_input(
                    "Enter a direct audio link (MP3/WAV):",
                    value="https://server8.mp3quran.net/afs/055.mp3",
                )
                if st.button("⚡ Process & Dampen Music", type="primary"):
                    if song_url:
                        with st.spinner(
                            f"Filtering instrumental frequencies for Stage {stage_num}..."
                        ):
                            processed_bytes = processor.process_track(
                                song_url, stage=stage_num
                            )
                            if processed_bytes:
                                st.success(f"Processing complete for Stage {stage_num}!")
                                st.audio(processed_bytes, format="audio/mp3")
                                st.session_state["active_cleansed_audio"] = processed_bytes
                                if stage_num == 2:
                                    reset_pause()   # each conversion needs a fresh pause
                            else:
                                st.warning(
                                    "⚠️ Could not fetch audio from that link. It must be a direct MP3/WAV link."
                                )
                                st.info(
                                    "💡 Try selecting 'Upload Audio File' above to process your file directly."
                                )
                    else:
                        st.warning("Please provide a valid audio URL.")
            else:
                uploaded_file = st.file_uploader(
                    "Upload Audio File (MP3/WAV/M4A):", type=["mp3", "wav", "m4a"]
                )
                if st.button("⚡ Process Uploaded File", type="primary"):
                    if uploaded_file:
                        with st.spinner(
                            f"Filtering instrumental frequencies for Stage {stage_num}..."
                        ):
                            processed_bytes = processor.process_track(
                                uploaded_file.getvalue(), stage=stage_num
                            )
                            if processed_bytes:
                                st.success(f"Processing complete for Stage {stage_num}!")
                                st.audio(processed_bytes, format="audio/mp3")
                                st.session_state["active_cleansed_audio"] = processed_bytes
                                if stage_num == 2:
                                    reset_pause()   # each conversion needs a fresh pause
                            else:
                                st.error("Failed to process the uploaded file.")
                    else:
                        st.warning("Please upload an audio file first.")

        elif stage_num == 2 and isinstance(st.session_state.get("active_cleansed_audio"), bytes):
            st.caption("Your last converted track:")
            st.audio(st.session_state["active_cleansed_audio"], format="audio/mp3")

    else:
        st.markdown("### Ambient Soundscape Layering")
        st.caption(
            "Add background soundscapes (rain, nature, ambient noise) over your audio."
        )

        default_source = st.session_state.get(
            "active_cleansed_audio", "https://server8.mp3quran.net/afs/055.mp3"
        )

        if isinstance(default_source, str):
            mixer_input = st.text_input("Audio Source for Mixing:", value=default_source)
        else:
            mixer_input = default_source
            st.info("Using your newly cleansed track from the previous step.")

        render_mixer(source=mixer_input)

# TAB 2: Context-Aware Audio Replacements
with tabs[1]:
    st.subheader("🎧 Context-Aware Audio Replacements")
    activity = st.selectbox(
        "What are you doing right now?",
        ["Working out", "Driving / Commuting", "Relaxing / Sleeping"],
    )

    category_map = {
        "Working out": "nasheed",
        "Driving / Commuting": "podcast",
        "Relaxing / Sleeping": "quran",
    }

    selected_category = category_map[activity]
    st.markdown(
        f"**Recommended for {activity}:** ({selected_category.title()} Selection)"
    )

    vault_tracks = vault.load_vault(
        _client=db.client, category=selected_category, trigger=activity
    )

    if vault_tracks:
        for track in vault_tracks:
            with st.container(border=True):
                title = track.get("title") or track.get("name") or "Untitled Track"
                creator = (
                    track.get("creator")
                    or track.get("reciter_artist")
                    or "Unknown Artist"
                )
                st.write(f"**{title}** — *{creator}*")
                st.audio(track.get("audio_url"))
    else:
        st.info(
            "No pre-loaded tracks found for this category yet. Showing default recommendations:"
        )
        st.audio("https://server8.mp3quran.net/afs/055.mp3")

# TAB 3: Live Mood Analytics (only the signed-in user's own entries)
with tabs[2]:
    analytics.render_analytics(_UserDB())

# TAB 4: Quran player & Dhikr counter
with tabs[3]:
    stage3.render_quran_and_dhikr()