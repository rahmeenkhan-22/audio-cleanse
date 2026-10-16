"""soundscapes.py: server-side ambient overlay for Audio Cleanse.

st.audio can't play two tracks in sync, so we mix on the server with pydub
(ffmpeg must be on PATH) and return ONE mp3 as bytes. Everything stays in
memory, so there are no temp files to clean up.

If an mp3 is missing from assets/soundscapes/, a synthetic rain / wind /
white-noise loop is generated instead, so the feature works with zero assets.
Drop in real recordings later (rain.mp3, desert_wind.mp3, white_noise.mp3).
"""
from __future__ import annotations

import io
import logging
import random
from functools import lru_cache
from pathlib import Path
from typing import Union

import requests
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
from pydub.generators import WhiteNoise

log = logging.getLogger(__name__)

ASSET_DIR = Path(__file__).parent / "assets" / "soundscapes"
MAX_FOREGROUND_MS = 30 * 60 * 1000        # refuse >30 min (RAM guard on free tier)
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
DOWNLOAD_TIMEOUT_S = 30

# display name -> (asset filename, synth fallback kind)
SOUNDSCAPES = {
    "Rain": ("rain.mp3", "rain"),
    "Desert Wind": ("desert_wind.mp3", "wind"),
    "Soft White Noise": ("white_noise.mp3", "white"),
}

Source = Union[str, Path, bytes, bytearray, io.IOBase]


class SoundscapeError(RuntimeError):
    """Safe to show to the user via st.error()."""


def list_soundscapes() -> list[str]:
    return list(SOUNDSCAPES)


# ---------- ambient sources ----------
def _synth(kind: str, ms: int = 30_000) -> AudioSegment:
    base = WhiteNoise().to_audio_segment(duration=ms, volume=-20.0)
    if kind == "rain":
        return base.high_pass_filter(1000).low_pass_filter(9000)
    if kind == "wind":
        low = base.low_pass_filter(600)
        rng = random.Random(7)

        def swell() -> AudioSegment:
            start = rng.randrange(0, ms - 4000)
            return low[start:start + 4000].apply_gain(rng.uniform(-10, 0))

        out = swell()
        while len(out) < ms:
            out = out.append(swell(), crossfade=2000)
        return out[:ms]
    return base.low_pass_filter(8000)


@lru_cache(maxsize=8)
def _load_ambient(name: str) -> AudioSegment:
    if name not in SOUNDSCAPES:
        raise SoundscapeError(f"Unknown soundscape: {name}")
    filename, kind = SOUNDSCAPES[name]
    path = ASSET_DIR / filename
    if path.exists():
        try:
            return AudioSegment.from_file(path)
        except CouldntDecodeError:
            log.warning("Could not decode %s, using synthetic fallback", path)
    return _synth(kind)


def _loop_to_length(seg: AudioSegment, target_ms: int) -> AudioSegment:
    """Loop with a crossfade. Doubling keeps it O(log n) in copies."""
    if len(seg) >= target_ms:
        return seg[:target_ms]
    xf = min(1500, len(seg) // 4)
    out = seg
    while len(out) < target_ms:
        out = out.append(out, crossfade=xf)
    return out[:target_ms]


# ---------- foreground sources ----------
def _download(url: str) -> bytes:
    try:
        with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT_S) as r:
            r.raise_for_status()
            buf, size = io.BytesIO(), 0
            for chunk in r.iter_content(1 << 16):
                size += len(chunk)
                if size > MAX_DOWNLOAD_BYTES:
                    raise SoundscapeError("That audio file is too large.")
                buf.write(chunk)
            return buf.getvalue()
    except requests.RequestException as e:
        log.exception("Download failed: %s", url)
        raise SoundscapeError("Couldn't download the audio.") from e


def _load_source(src: Source) -> AudioSegment:
    try:
        if isinstance(src, (bytes, bytearray)):
            return AudioSegment.from_file(io.BytesIO(bytes(src)))
        if isinstance(src, str) and src.startswith(("http://", "https://")):
            return AudioSegment.from_file(io.BytesIO(_download(src)))
        if hasattr(src, "read"):                      # e.g. Streamlit UploadedFile
            if hasattr(src, "seek"):
                src.seek(0)
            return AudioSegment.from_file(io.BytesIO(src.read()))
        return AudioSegment.from_file(str(src))
    except CouldntDecodeError as e:
        raise SoundscapeError("Couldn't read that audio file.") from e
    except FileNotFoundError as e:
        raise SoundscapeError("Audio file not found (or ffmpeg is not installed).") from e


# ---------- public API ----------
def mix_with_soundscape(
    source: Source,
    soundscape: str,
    level: float = 0.5,
    *,
    fade_ms: int = 3000,
    bitrate: str = "128k",
) -> bytes:
    """Overlay `soundscape` beneath `source`; return mp3 bytes.

    level: 0.0 to 1.0. Ambient loudness is set RELATIVE to the foreground
    (0.0 = 30 dB below, 0.5 = 18 dB below, 1.0 = 6 dB below), so recitation
    stays clear no matter how loud the original file is.
    """
    fg = _load_source(source)
    if len(fg) == 0 or fg.dBFS == float("-inf"):
        raise SoundscapeError("The audio is empty or silent.")
    if len(fg) > MAX_FOREGROUND_MS:
        raise SoundscapeError("Tracks longer than 30 minutes aren't supported.")

    level = min(max(level, 0.0), 1.0)
    rel_db = -30 + 24 * level
    fade = min(fade_ms, len(fg) // 4)

    amb = _load_ambient(soundscape).set_frame_rate(fg.frame_rate).set_channels(fg.channels)
    amb = _loop_to_length(amb, len(fg))
    amb = amb.apply_gain(fg.dBFS + rel_db - amb.dBFS).fade_in(fade).fade_out(fade)

    mixed = fg.overlay(amb)
    if mixed.max_dBFS > -1.0:                         # avoid clipping
        mixed = mixed.apply_gain(-1.0 - mixed.max_dBFS)

    buf = io.BytesIO()
    try:
        mixed.export(buf, format="mp3", bitrate=bitrate)
    except Exception as e:                            # ffmpeg/lame failures
        log.exception("Export failed")
        raise SoundscapeError("Couldn't export the mixed audio.") from e
    return buf.getvalue()


def preview_soundscape(name: str, seconds: int = 15) -> bytes:
    """Short mp3 clip of the ambient alone, for a 'Preview' button."""
    clip = _load_ambient(name)[: seconds * 1000].fade_in(1000).fade_out(1000)
    buf = io.BytesIO()
    clip.export(buf, format="mp3", bitrate="96k")
    return buf.getvalue()
