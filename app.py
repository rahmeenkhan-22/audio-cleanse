import streamlit as st
import vault
import pandas as pd
import time
from database import DatabaseManager
from audio_processor import AudioProcessor
from analytics import render_mood_analytics
from ui_components import render_mixer, pause_and_reflect, reset_pause

# Page Configuration
st.set_page_config(
    page_title="Audio Cleanse - Music Transition App",
    page_icon="🎵",
    layout="wide"
)

# Initialize Core Services
db = DatabaseManager()
processor = AudioProcessor()

# Session State Initialization
if "user_day" not in st.session_state:
    st.session_state.user_day = 1

# Calculate Current Stage
if st.session_state.user_day <= 14:
    current_stage = 1
elif st.session_state.user_day <= 35:
    current_stage = 2
else:
    current_stage = 3

# App Header & Stage Progress Bar
st.title("🛡️ Audio Cleanse")
st.caption("A guided journey to transition away from instrumental music.")

col1, col2, col3 = st.columns(3)
col1.metric("Journey Day", f"Day {st.session_state.user_day}")
col2.metric("Current Stage", f"Stage {current_stage}")
col3.metric("Status", "Active" if current_stage < 3 else "Pure Dhikr")

progress_val = min(st.session_state.user_day / 36, 1.0)
st.progress(progress_val)

st.divider()

# Sidebar: Stage Overrides & Mood Logging
with st.sidebar:
    st.header("⚙️ User Controls")
    
    # Day Simulator (For testing stage unlocks)
    st.session_state.user_day = st.slider("Simulate Journey Day", 1, 40, st.session_state.user_day)
    
    st.divider()
    st.subheader("📝 Daily Craving & Mood Log")
    with st.form("mood_form"):
        craving = st.slider("Music Craving Intensity (1-10)", 1, 10, 5)
        context = st.selectbox("Trigger Context", ["Driving", "Working out", "Stressed", "Bored", "Relaxing"])
        emotion = st.selectbox("Emotional State", ["Anxious", "Calm", "Energetic", "Tired", "Overwhelmed"])
        submitted = st.form_submit_button("Log Entry")
        
        if submitted:
            # Standard test user UUID for local testing
            db.log_mood_craving("00000000-0000-0000-0000-000000000000", craving, context, emotion)
            st.success("Mood log saved!")

# Main Feature Area Based on Stage
tabs = st.tabs(["🎵 Audio Cleanse Engine", "🎧 Replacing the Trigger", "📊 Mood Analytics"])

with tabs[0]:
    if current_stage == 1:
        st.subheader("Stage 1: AI Vocal Extraction Engine (Days 1–14)")
        st.info("Upload an audio file or paste a YouTube URL. Demucs AI will strip background instruments and isolate vocals.")
        
        input_type = st.radio("Choose Input Method", ["File Upload", "Paste YouTube URL"])
        
        if input_type == "File Upload":
            uploaded_file = st.file_uploader("Upload Audio Track (.mp3, .wav)", type=["mp3", "wav"])
            if uploaded_file is not None and st.button("Extract Vocals from File"):
                with st.spinner("Processing audio with Demucs AI..."):
                    try:
                        result = processor.process_audio(uploaded_file.read(), uploaded_file.name)
                        st.success(f"Extraction complete! (Source: {result['status']})")
                        st.audio(result["storage_url"])
                    except Exception as e:
                        st.error(f"Error processing audio: {e}")
                    
        else:
            yt_url = st.text_input("Paste YouTube Video URL:")
            if yt_url and st.button("Extract Vocals from Link"):
                with st.spinner("Downloading YouTube audio and running Demucs..."):
                    try:
                        result = processor.process_yt_url(yt_url)
                        st.success(f"Extraction complete! (Source: {result['status']})")
                        st.audio(result["storage_url"])
                    except Exception as e:
                        st.error(f"Error processing YouTube video: {e}")

    elif current_stage == 2:
        st.subheader("Stage 2: Throttled Conversion & Transition (Days 15–35)")
        st.warning("Conversion power is throttled. Take a moment to reflect before processing new audio.")

        if pause_and_reflect():
            input_type = st.radio("Choose Input Method", ["File Upload", "Paste YouTube URL"], key="stage2_input")

            if input_type == "File Upload":
                uploaded_file = st.file_uploader("Upload Audio Track (.mp3, .wav)", type=["mp3", "wav"], key="stage2_file")
                if uploaded_file and st.button("Proceed with Throttled File Extraction"):
                    with st.spinner("Extracting..."):
                        try:
                            result = processor.process_audio(uploaded_file.read(), uploaded_file.name)
                            st.audio(result["storage_url"])
                            reset_pause()
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                yt_url = st.text_input("Paste YouTube Video URL:", key="stage2_yt")
                if yt_url and st.button("Proceed with Throttled Link Extraction"):
                    with st.spinner("Extracting from YouTube..."):
                        try:
                            result = processor.process_yt_url(yt_url)
                            st.audio(result["storage_url"])
                            reset_pause()
                        except Exception as e:
                            st.error(f"Error: {e}")

    else:
        st.subheader("Stage 3: Pure Quran & Dhikr Mode (Day 36+)")
        st.error("Audio converter is locked. You have reached Stage 3: Pure Dhikr!")
        st.success("Congratulations on reaching full transition! Explore vocal-only recitations and ambient soundscapes in the 'Replacing the Trigger' tab.")

with tabs[1]:
    st.subheader("🎧 Context-Aware Audio Replacements")
    activity = st.selectbox("What are you doing right now?", ["Working out", "Driving / Commuting", "Relaxing / Sleeping"])
    
    # Map activity to vault category
    category_map = {
        "Working out": "Nasheed",
        "Driving / Commuting": "Lectures",
        "Relaxing / Sleeping": "Quran"
    }
    
    selected_category = category_map[activity]
    st.markdown(f"**Recommended for {activity}:** ({selected_category} Selection)")
    
    # Load tracks from Vault
    vault_tracks = vault.load_vault(db, category=selected_category)
    
    if vault_tracks:
        for track in vault_tracks:
            with st.container(border=True):
                st.write(f"**{track.get('title', 'Untitled')}** — {track.get('reciter_artist', 'Unknown')}")
                st.audio(track.get('audio_url'))
    else:
        st.info("No pre-loaded tracks found for this category yet. Showing default recommendations:")
        if activity == "Working out":
            st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")
        elif activity == "Driving / Commuting":
            st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3")
        else:
            st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3")
            
with tabs[2]:
    st.subheader("📊 Your Craving & Mood Progress")
    try:
        response = db.client.table("mood_analytics").select("*").execute()
        df = pd.DataFrame(response.data)
        render_mood_analytics(df)
    except Exception as e:
        st.info("Log your daily mood in the sidebar to generate graphs!")

