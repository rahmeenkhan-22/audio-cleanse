"""
audio_processor.py: DSP frequency filtering and robust audio fetching for Audio Cleanse.
"""
import io
import os
import tempfile
import logging
import requests
import yt_dlp
from pydub import AudioSegment
from pydub.scipy_effects import high_pass_filter, low_pass_filter

log = logging.getLogger(__name__)


class AudioProcessor:
    def __init__(self):
        pass

    def _fetch_audio_bytes(self, source: str) -> bytes:
        """Fetches raw audio bytes from YouTube or direct HTTP URLs safely."""
        if "youtube.com" in source or "youtu.be" in source:
            with tempfile.TemporaryDirectory() as temp_dir:
                output_template = os.path.join(temp_dir, 'yt_audio.%(ext)s')
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': output_template,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'quiet': True,
                    'no_warnings': True,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([source])
                
                mp3_path = os.path.join(temp_dir, 'yt_audio.mp3')
                if os.path.exists(mp3_path):
                    with open(mp3_path, 'rb') as f:
                        return f.read()
                raise FileNotFoundError("Could not process YouTube audio stream.")
        
        # Direct URL fetch with realistic browser headers
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(source, headers=headers, timeout=15)
        response.raise_for_status()
        return response.content

    def process_track(self, audio_source, stage: int = 1) -> bytes:
        """
        Applies stage-based DSP frequency filtering to direct URLs, uploaded bytes, or local files.
        """
        try:
            # 1. Resolve to raw audio bytes
            if isinstance(audio_source, bytes):
                raw_bytes = audio_source
            elif isinstance(audio_source, str) and (audio_source.startswith("http://") or audio_source.startswith("https://")):
                raw_bytes = self._fetch_audio_bytes(audio_source)
            else:
                with open(audio_source, 'rb') as f:
                    raw_bytes = f.read()

            audio = AudioSegment.from_file(io.BytesIO(raw_bytes))

            # 2. Stage-based DSP Filtering
            if stage == 1:
                filtered = high_pass_filter(audio, cutoff=200)
                filtered = filtered - 1.5
            elif stage == 2:
                filtered = high_pass_filter(audio, cutoff=300)
                filtered = low_pass_filter(filtered, cutoff=3400)
                filtered = filtered - 3.0
            else:
                filtered = high_pass_filter(audio, cutoff=400)
                filtered = low_pass_filter(filtered, cutoff=3000)
                filtered = filtered - 5.0

            # 3. Export to MP3 buffer
            buffer = io.BytesIO()
            filtered.export(buffer, format="mp3")
            buffer.seek(0)
            return buffer.getvalue()

        except Exception as e:
            log.exception(f"Error processing track for Stage {stage}: {e}")
            return None