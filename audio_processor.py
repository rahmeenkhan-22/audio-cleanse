"""
audio_processor.py: Lightweight DSP frequency filtering for Audio Cleanse.
Applies stage-aware high-pass and low-pass filtering using PyDub and standard Python libraries.
"""
import io
import logging
import urllib.request
from pydub import AudioSegment
from pydub.scipy_effects import high_pass_filter, low_pass_filter

log = logging.getLogger(__name__)


class AudioProcessor:
    def __init__(self):
        pass

    def process_track(self, audio_source: str, stage: int = 1) -> bytes:
        """
        Fetches audio from a URL or bytes buffer and applies frequency attenuation
        tuned to the user's current Journey Stage.
        """
        try:
            # 1. Fetch audio content
            if isinstance(audio_source, bytes):
                audio = AudioSegment.from_file(io.BytesIO(audio_source))
            elif isinstance(audio_source, str) and (audio_source.startswith("http://") or audio_source.startswith("https://")):
                req = urllib.request.Request(
                    audio_source, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req) as response:
                    audio_bytes = response.read()
                audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            else:
                audio = AudioSegment.from_file(audio_source)

            # 2. Stage-aware DSP Filtering
            if stage == 1:
                # Cut sub-bass frequencies below 200Hz to weaken heavy beats
                filtered = high_pass_filter(audio, cutoff=200)
                filtered = filtered - 1.5
            elif stage == 2:
                # Bandpass filter for vocal speech range (300Hz - 3400Hz)
                filtered = high_pass_filter(audio, cutoff=300)
                filtered = low_pass_filter(filtered, cutoff=3400)
                filtered = filtered - 3.0
            else:
                # Aggressive vocal isolation (400Hz - 3000Hz)
                filtered = high_pass_filter(audio, cutoff=400)
                filtered = low_pass_filter(filtered, cutoff=3000)
                filtered = filtered - 5.0

            buffer = io.BytesIO()
            filtered.export(buffer, format="mp3")
            buffer.seek(0)
            return buffer.getvalue()

        except Exception as e:
            log.exception(f"Error processing track DSP for Stage {stage}: {e}")
            return None