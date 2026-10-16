"""
audio_processor.py: Audio stream handler and DSP frequency filtering module.
Supports YouTube links (via yt-dlp), direct MP3/WAV URLs, uploaded file bytes, and stage DSP filtering.
"""
import io
import os
import tempfile
import urllib.request
import logging
import yt_dlp
from pydub import AudioSegment
from pydub.scipy_effects import high_pass_filter, low_pass_filter

log = logging.getLogger(__name__)


class AudioProcessor:
    def __init__(self):
        pass

    def _download_youtube_audio(self, url: str) -> bytes:
        """Extracts raw WAV audio bytes from a YouTube URL using yt-dlp."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_template = os.path.join(temp_dir, 'yt_audio.%(ext)s')
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_template,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            wav_path = os.path.join(temp_dir, 'yt_audio.wav')
            if os.path.exists(wav_path):
                with open(wav_path, 'rb') as f:
                    return f.read()
            else:
                raise FileNotFoundError("Failed to extract YouTube audio file.")

    def process_track(self, audio_source, stage: int = 1) -> bytes:
        """
        Fetches audio from YouTube URL, direct MP3 URL, or raw bytes buffer,
        then applies stage-based frequency attenuation.
        """
        try:
            # 1. Obtain raw audio bytes
            if isinstance(audio_source, bytes):
                audio = AudioSegment.from_file(io.BytesIO(audio_source))
            elif isinstance(audio_source, str) and ("youtube.com" in audio_source or "youtu.be" in audio_source):
                # Process YouTube link via yt-dlp
                raw_bytes = self._download_youtube_audio(audio_source)
                audio = AudioSegment.from_file(io.BytesIO(raw_bytes))
            elif isinstance(audio_source, str) and (audio_source.startswith("http://") or audio_source.startswith("https://")):
                # Process direct audio file URL (e.g. .mp3 / .wav)
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
                # Stage 1: Sub-bass attenuation below 200 Hz
                filtered = high_pass_filter(audio, cutoff=200)
                filtered = filtered - 1.5
            elif stage == 2:
                # Stage 2: Vocal bandpass filter (300 Hz - 3400 Hz)
                filtered = high_pass_filter(audio, cutoff=300)
                filtered = low_pass_filter(filtered, cutoff=3400)
                filtered = filtered - 3.0
            else:
                # Stage 3: Strict vocal band (400 Hz - 3000 Hz)
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