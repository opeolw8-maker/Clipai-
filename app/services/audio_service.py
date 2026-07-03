"""Extracts a mono 16kHz WAV track from a video, for transcription."""
import subprocess
from dataclasses import dataclass

from app.infrastructure.ffmpeg_locator import FFmpegLocator


@dataclass
class AudioExtractor:
    ffmpeg: FFmpegLocator

    def extract(self, video_path: str, audio_path: str) -> None:
        ffmpeg_exe = self.ffmpeg.ffmpeg_exe()
        subprocess.run(
            [ffmpeg_exe, "-i", video_path, "-vn", "-acodec", "pcm_s16le",
             "-ar", "16000", "-ac", "1", audio_path, "-y", "-loglevel", "error"],
            check=True,
      )
