import time
import pandas as pd
import streamlit as st

import analytics
from audio_processor import AudioProcessor
from database import DatabaseManager
import ui_components
from ui_components import pause_and_reflect, render_mixer, reset_pause
import vault

# --- Page Configuration ---
st.set_page_config(
    page_title="Audio Cleanse",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Database & Service Initialization ---
db = DatabaseManager()
processor = AudioProcessor()

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
    success = db.log_mood(
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

# --- Pause & Reflect Exercise ---
pause_and_reflect()

# --- APP TABS ---
tabs = st.tabs(
    ["🎵 Audio Cleanse Engine", "🎧 Replacing the Trigger", "📊 Mood Analytics"]
)

# TAB 1: Cleanse Engine & Mixer
with tabs[0]:
    st.subheader("🎵 Audio Cleanse Processing Engine")
    
    # Mode selection for user workflow
    engine_mode = st.radio(
        "Choose Operation:",
        ["🎼 Convert / Remove Instrumental Music", "🎛️ Ambient Soundscape Mixer"],
        horizontal=True
    )
    
    st.divider()
    
    if engine_mode == "🎼 Convert / Remove Instrumental Music":
        st.markdown("### Remove or Dampen Instrumental Music")
        st.caption("Submit a song link to isolate vocals or apply stage-based frequency dampening.")
        
        song_url = st.text_input("Enter Song or YouTube URL:")
        
        if st.button("⚡ Process & Remove Music", type="primary"):
            if song_url:
                with st.spinner(f"Filtering instrumental frequencies for Stage {stage_num}..."):
                    processed_track = processor.process_track(song_url, stage=stage_num)
                    time.sleep(1)
                    st.success("Instrumental conversion complete!")
                    
                    if processed_track:
                        st.audio(processed_track)
                        # Option to send processed track straight into the mixer
                        st.session_state["active_cleansed_audio"] = processed_track
            else:
                st.warning("Please provide a valid audio link to process.")

    else:
        st.markdown("### Ambient Soundscape Layering")
        st.caption("Add soothing background ambience (rain, birds, white noise) to your audio.")
        
        # Default to recently cleansed audio if available, otherwise ask for source
        default_source = st.session_state.get("active_cleansed_audio", "https://server8.mp3quran.net/afs/055.mp3")
        mixer_input = st.text_input("Audio Source for Mixing:", value=default_source)
        
        if mixer_input:
            render_mixer(source=mixer_input)
        else:
            st.info("Provide an audio link or convert a song first to use the mixer.")

            
# TAB 2: Context-Aware Audio Replacements
with tabs[1]:
    st.subheader("🎧 Context-Aware Audio Replacements")
    activity = st.selectbox(
        "What are you doing right now?",
        ["Working out", "Driving / Commuting", "Relaxing / Sleeping"],
    )

    # Category mapping (lowercase to match catalog/vault)
    category_map = {
        "Working out": "nasheed",
        "Driving / Commuting": "podcast",
        "Relaxing / Sleeping": "quran",
    }

    selected_category = category_map[activity]
    st.markdown(
        f"**Recommended for {activity}:** ({selected_category.title()} Selection)"
    )

    # Load replacement tracks from Supabase or local vault catalog
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

# TAB 3: Live Mood Analytics
with tabs[2]:
    analytics.render_analytics(db)