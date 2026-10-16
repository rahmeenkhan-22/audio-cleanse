"""ui_components.py: reusable Streamlit widgets for app.py.

- render_mixer():       soundscape overlay UI (uses soundscapes.py)
- pause_and_reflect():  30-second countdown with rotating ayat / hadith

Requires streamlit >= 1.37 (st.fragment with run_every).
"""
from __future__ import annotations

import html
import math
import time
from typing import Callable, Optional

import streamlit as st

import soundscapes

# =====================================================================
# Soundscape mixer
# =====================================================================
@st.cache_data(show_spinner=False, max_entries=4, ttl=3600)
def _cached_mix(source, soundscape: str, level: float) -> bytes:
    return soundscapes.mix_with_soundscape(source, soundscape, level)


def render_mixer(source, *, key: str = "mixer", file_stem: str = "audio_cleanse_mix") -> None:
    """`source` = URL string, bytes, or a path (not a live UploadedFile; pass .getvalue())."""
    c1, c2 = st.columns([2, 1])
    choice = c1.selectbox("Background soundscape", soundscapes.list_soundscapes(), key=f"{key}_sc")
    level = c2.slider("Ambient level", 0.0, 1.0, 0.5, 0.05, key=f"{key}_lvl")

    if st.button("Preview ambient (15s)", key=f"{key}_prev"):
        st.audio(soundscapes.preview_soundscape(choice), format="audio/mp3")

    if st.button("🎚️ Mix", key=f"{key}_mix", type="primary"):
        with st.spinner("Mixing tracks…"):
            try:
                st.session_state[f"{key}_out"] = _cached_mix(source, choice, level)
            except soundscapes.SoundscapeError as e:
                st.session_state.pop(f"{key}_out", None)
                st.error(str(e))
            except Exception:
                st.session_state.pop(f"{key}_out", None)
                st.error("Something went wrong while mixing. Please try again.")

    out = st.session_state.get(f"{key}_out")
    if out:
        st.audio(out, format="audio/mp3")
        st.download_button("⬇️ Download mix", out, file_name=f"{file_stem}.mp3",
                           mime="audio/mpeg", key=f"{key}_dl")


# =====================================================================
# Pause & Reflect
# =====================================================================
# Please verify every Arabic text and translation against a mushaf / Quran.com
# before shipping. Add or swap entries freely.
REFLECTIONS = [
    {"ar": "أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ",
     "en": "Verily, in the remembrance of Allah do hearts find rest.",
     "ref": "Quran 13:28"},
    {"ar": "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا",
     "en": "For indeed, with hardship comes ease.",
     "ref": "Quran 94:5"},
    {"ar": "لَا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا",
     "en": "Allah does not burden a soul beyond what it can bear.",
     "ref": "Quran 2:286"},
    {"ar": "وَمَن يَتَّقِ اللَّهَ يَجْعَل لَّهُ مَخْرَجًا",
     "en": "Whoever is mindful of Allah, He will make a way out for him.",
     "ref": "Quran 65:2"},
    {"ar": "لَا تَقْنَطُوا مِن رَّحْمَةِ اللَّهِ",
     "en": "Do not despair of the mercy of Allah.",
     "ref": "Quran 39:53"},
    {"ar": "",
     "en": "Every son of Adam makes mistakes, and the best of those who make "
           "mistakes are those who repent.",
     "ref": "Hadith, Tirmidhi"},
]
ROTATE_EVERY_S = 6


def _k(key: str, name: str) -> str:
    return f"{key}_{name}"


def reset_pause(key: str = "pr") -> None:
    """Call after a conversion starts so the next one needs a new pause."""
    for name in ("state", "started_at"):
        st.session_state.pop(_k(key, name), None)


def _fire(cb: Optional[Callable[[], None]]) -> None:
    if cb:
        try:
            cb()
        except Exception:
            pass          # logging must never block the UI


@st.fragment(run_every=1)
def _countdown(key: str, seconds: int, on_abandon: Optional[Callable[[], None]]) -> None:
    start = st.session_state.get(_k(key, "started_at"))
    if start is None:
        return
    elapsed = time.monotonic() - start
    remaining = max(0, math.ceil(seconds - elapsed))

    if remaining == 0:
        st.session_state[_k(key, "state")] = "ready"
        st.rerun()                                   # full-app rerun, stops the timer

    item = REFLECTIONS[int(elapsed // ROTATE_EVERY_S) % len(REFLECTIONS)]
    st.progress(min(1.0, elapsed / seconds), text=f"Take a breath… {remaining}s")
    if item["ar"]:
        st.markdown(
            f"<div dir='rtl' style='text-align:center;font-size:1.9rem;line-height:2.4rem;"
            f"margin:0.8rem 0'>{html.escape(item['ar'])}</div>",
            unsafe_allow_html=True,
        )
    st.markdown(f"<div style='text-align:center;font-size:1.05rem'>{html.escape(item['en'])}</div>"
                f"<div style='text-align:center;opacity:.6;font-size:.85rem;margin-top:.3rem'>"
                f"{html.escape(item['ref'])}</div>", unsafe_allow_html=True)

    if st.button("I'll stop here", key=_k(key, "stop")):
        _fire(on_abandon)
        reset_pause(key)
        st.rerun()


def pause_and_reflect(
    *,
    key: str = "pr",
    seconds: int = 30,
    on_complete: Optional[Callable[[], None]] = None,
    on_abandon: Optional[Callable[[], None]] = None,
) -> bool:
    """Stage-2 gate. Returns True once the user finished the countdown AND confirmed.

    States: idle -> counting -> ready -> granted. State lives in st.session_state
    (server-side), so refreshing the page restarts the pause instead of skipping it.
    After starting the conversion, call reset_pause(key).
    """
    state = st.session_state.get(_k(key, "state"), "idle")

    if state == "granted":
        return True

    if state == "idle":
        if st.button("🎧 I want to convert a song", key=_k(key, "begin")):
            st.session_state[_k(key, "state")] = "counting"
            st.session_state[_k(key, "started_at")] = time.monotonic()
            st.rerun()
        return False

    if state == "counting":
        _countdown(key, seconds, on_abandon)
        return False

    if state == "ready":
        st.success("You paused. The choice is still yours.")
        c1, c2 = st.columns(2)
        if c1.button("Continue to conversion", key=_k(key, "go"), type="primary"):
            _fire(on_complete)
            st.session_state[_k(key, "state")] = "granted"
            st.rerun()
        if c2.button("Skip it, I'm good", key=_k(key, "skip")):
            _fire(on_abandon)
            reset_pause(key)
            st.rerun()
    return False
