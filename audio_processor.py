import os
import hashlib
import tempfile
import subprocess
from database import DatabaseManager
import yt_dlp

class AudioProcessor:
    def __init__(self):
        self.db = DatabaseManager()

    def generate_md5_hash(self, file_bytes: bytes) -> str:
        return hashlib.md5(file_bytes).hexdigest()

    def download_yt_audio(self, url: str, output_dir: str) -> str:
        """Downloads audio from a YouTube link using yt-dlp with updated bypass headers."""
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_dir, 'yt_audio.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web']
                }
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return os.path.join(output_dir, 'yt_audio.wav')

    def process_yt_url(self, url: str) -> dict:
        """Processes a YouTube URL directly."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        cached_record = self.db.get_cached_audio(url_hash)
        if cached_record:
            return {
                "status": "cached",
                "storage_url": cached_record["storage_url"],
                "file_hash": url_hash,
                "title": cached_record["track_title"]
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = self.download_yt_audio(url, temp_dir)
            output_dir = os.path.join(temp_dir, "separated")

            cmd = [
                "demucs",
                "--two-stems=vocals",
                "-n", "htdemucs",
                "-o", output_dir,
                audio_path
            ]
            
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Demucs processing failed: {e.stderr.decode('utf-8')}")

            vocal_file = os.path.join(output_dir, "htdemucs", "yt_audio", "vocals.wav")

            storage_path = f"extracted/{url_hash}.wav"
            with open(vocal_file, "rb") as vf:
                self.db.client.storage.from_("processed_audio").upload(
                    path=storage_path,
                    file=vf,
                    file_options={"content-type": "audio/wav"}
                )

            public_url = self.db.client.storage.from_("processed_audio").get_public_url(storage_path)

            self.db.save_audio_cache(
                file_hash=url_hash,
                track_title="YouTube Track",
                storage_url=public_url
            )

            return {
                "status": "processed",
                "storage_url": public_url,
                "file_hash": url_hash,
                "title": "YouTube Track"
            }

    def process_audio(self, file_bytes: bytes, filename: str) -> dict:
        file_hash = self.generate_md5_hash(file_bytes)
        
        cached_record = self.db.get_cached_audio(file_hash)
        if cached_record:
            return {
                "status": "cached",
                "storage_url": cached_record["storage_url"],
                "file_hash": file_hash,
                "title": cached_record["track_title"]
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, filename)
            output_dir = os.path.join(temp_dir, "separated")
            
            with open(input_path, "wb") as f:
                f.write(file_bytes)

            cmd = [
                "demucs",
                "--two-stems=vocals",
                "-n", "htdemucs",
                "-o", output_dir,
                input_path
            ]
            
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Demucs processing failed: {e.stderr.decode('utf-8')}")

            track_name = os.path.splitext(filename)[0]
            vocal_file = os.path.join(output_dir, "htdemucs", track_name, "vocals.wav")

            storage_path = f"extracted/{file_hash}.wav"
            with open(vocal_file, "rb") as vf:
                self.db.client.storage.from_("processed_audio").upload(
                    path=storage_path,
                    file=vf,
                    file_options={"content-type": "audio/wav"}
                )

            public_url = self.db.client.storage.from_("processed_audio").get_public_url(storage_path)

            self.db.save_audio_cache(
                file_hash=file_hash,
                track_title=track_name,
                storage_url=public_url
            )

            return {
                "status": "processed",
                "storage_url": public_url,
                "file_hash": file_hash,
                "title": track_name
            }