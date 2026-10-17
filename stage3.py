"""stage3.py: Quran player + Dhikr counter for Audio Cleanse.

Needs the `dhikr_logs` table in Supabase (see dhikr SQL) for the Save button.
The Quran player works without it.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import streamlit as st

from auth import current_user, user_client
from ui_components import render_mixer

log = logging.getLogger(__name__)

# ---------------------------------------------------------------- Quran data
# {n:03d} is the surah number padded to 3 digits (e.g. 055).
# Add more reciters by adding another entry with that reciter's URL template.
RECITERS = {
    "Mishary Rashid Alafasy": "https://server8.mp3quran.net/afs/{n:03d}.mp3",
}

SURAHS = [
    "Al-Fatihah", "Al-Baqarah", "Ali 'Imran", "An-Nisa", "Al-Ma'idah", "Al-An'am",
    "Al-A'raf", "Al-Anfal", "At-Tawbah", "Yunus", "Hud", "Yusuf", "Ar-Ra'd", "Ibrahim",
    "Al-Hijr", "An-Nahl", "Al-Isra", "Al-Kahf", "Maryam", "Ta-Ha", "Al-Anbiya", "Al-Hajj",
    "Al-Mu'minun", "An-Nur", "Al-Furqan", "Ash-Shu'ara", "An-Naml", "Al-Qasas",
    "Al-'Ankabut", "Ar-Rum", "Luqman", "As-Sajdah", "Al-Ahzab", "Saba", "Fatir", "Ya-Sin",
    "As-Saffat", "Sad", "Az-Zumar", "Ghafir", "Fussilat", "Ash-Shura", "Az-Zukhruf",
    "Ad-Dukhan", "Al-Jathiyah", "Al-Ahqaf", "Muhammad", "Al-Fath", "Al-Hujurat", "Qaf",
    "Adh-Dhariyat", "At-Tur", "An-Najm", "Al-Qamar", "Ar-Rahman", "Al-Waqi'ah", "Al-Hadid",
    "Al-Mujadila", "Al-Hashr", "Al-Mumtahanah", "As-Saff", "Al-Jumu'ah", "Al-Munafiqun",
    "At-Taghabun", "At-Talaq", "At-Tahrim", "Al-Mulk", "Al-Qalam", "Al-Haqqah",
    "Al-Ma'arij", "Nuh", "Al-Jinn", "Al-Muzzammil", "Al-Muddaththir", "Al-Qiyamah",
    "Al-Insan", "Al-Mursalat", "An-Naba", "An-Nazi'at", "'Abasa", "At-Takwir",
    "Al-Infitar", "Al-Mutaffifin", "Al-Inshiqaq", "Al-Buruj", "At-Tariq", "Al-A'la",
    "Al-Ghashiyah", "Al-Fajr", "Al-Balad", "Ash-Shams", "Al-Layl", "Ad-Duha", "Ash-Sharh",
    "At-Tin", "Al-'Alaq", "Al-Qadr", "Al-Bayyinah", "Az-Zalzalah", "Al-'Adiyat",
    "Al-Qari'ah", "At-Takathur", "Al-'Asr", "Al-Humazah", "Al-Fil", "Quraysh", "Al-Ma'un",
    "Al-Kawthar", "Al-Kafirun", "An-Nasr", "Al-Masad", "Al-Ikhlas", "Al-Falaq", "An-Nas",
]
assert len(SURAHS) == 114

# ---------------------------------------------------------------- Dhikr data
# name -> (Arabic, meaning, default target)
DHIKR = {
    "SubhanAllah": ("سُبْحَانَ اللَّهِ", "Glory be to Allah", 33),
    "Alhamdulillah": ("الْحَمْدُ لِلَّهِ", "All praise is for Allah", 33),
    "Allahu Akbar": ("اللَّهُ أَكْبَرُ", "Allah is the Greatest", 34),
    "La ilaha illa Allah": ("لَا إِلَٰهَ إِلَّا اللَّهُ", "There is no god but Allah", 100),
    "Astaghfirullah": ("أَسْتَغْفِرُ اللَّهَ", "I seek forgiveness from Allah", 100),
}


# ---------------------------------------------------------------- DB helpers
def save_dhikr(name: str, count: int) -> bool:
    client, user = user_client(), current_user()
    if not client or not user or count <= 0:
        return False
    try:
        client.table("dhikr_logs").insert(
            {"user_id": user["id"], "dhikr": name, "count": int(count)}
        ).execute()
        return True
    except Exception:
        log.exception("Failed to save dhikr")
        return False


def load_dhikr_last_24h() -> dict[str, int]:
    client, user = user_client(), current_user()
    if not client or not user:
        return {}
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    try:
        rows = (client.table("dhikr_logs").select("dhikr,count")
                .eq("user_id", user["id"]).gte("created_at", since).execute().data or [])
    except Exception:
        log.exception("Failed to load dhikr")
        return {}
    totals: dict[str, int] = {}
    for r in rows:
        totals[r["dhikr"]] = totals.get(r["dhikr"], 0) + r["count"]
    return totals


# ---------------------------------------------------------------- UI
def _render_quran() -> None:
    c1, c2 = st.columns(2)
    reciter = c1.selectbox("Reciter", list(RECITERS), key="q_reciter")
    n = c2.selectbox(
        "Surah", list(range(1, 115)), format_func=lambda i: f"{i}. {SURAHS[i - 1]}", key="q_surah"
    )
    url = RECITERS[reciter].format(n=n)
    st.audio(url)
    st.caption("Recitations are streamed from mp3quran.net.")

    with st.expander("🌧️ Add a background soundscape (works best for shorter surahs)"):
        render_mixer(url, key=f"s3_mix_{reciter}_{n}", file_stem=f"surah_{n:03d}_soundscape")


def _render_dhikr() -> None:
    counts = st.session_state.setdefault("dhikr_counts", {})
    name = st.selectbox("Dhikr", list(DHIKR), key="dhikr_name")
    arabic, meaning, default_target = DHIKR[name]

    st.markdown(
        f"<div dir='rtl' style='text-align:center;font-size:2.2rem;margin:.6rem 0'>{arabic}</div>"
        f"<div style='text-align:center;opacity:.7'>{meaning}</div>",
        unsafe_allow_html=True,
    )

    target = st.number_input("Target", min_value=1, max_value=10000,
                             value=default_target, step=1, key=f"dhikr_target_{name}")
    count = counts.get(name, 0)

    st.markdown(
        f"<div style='text-align:center;font-size:3.5rem;font-weight:700'>{count}</div>",
        unsafe_allow_html=True,
    )
    st.progress(min(count / target, 1.0), text=f"{count} / {target}")
    if count >= target:
        st.success("Target reached. May Allah accept it.")

    b1, b2, b3, b4 = st.columns(4)
    if b1.button("➕ Tap", key="dhikr_tap", type="primary"):
        counts[name] = count + 1
        st.rerun()
    if b2.button("↩️ Undo", key="dhikr_undo") and count > 0:
        counts[name] = count - 1
        st.rerun()
    if b3.button("🔄 Reset", key="dhikr_reset"):
        counts[name] = 0
        st.rerun()
    if b4.button("💾 Save", key="dhikr_save"):
        if save_dhikr(name, count):
            counts[name] = 0
            st.rerun()
        else:
            st.error("Nothing to save, or saving failed.")

    st.divider()
    st.markdown("**Your dhikr in the last 24 hours**")
    totals = load_dhikr_last_24h()
    if totals:
        for k, v in totals.items():
            st.write(f"{k}: **{v}**")
    else:
        st.caption("Nothing saved yet. Press Save after a session.")


def render_quran_and_dhikr() -> None:
    quran_tab, dhikr_tab = st.tabs(["📖 Quran", "📿 Dhikr"])
    with quran_tab:
        _render_quran()
    with dhikr_tab:
        _render_dhikr()
