"""Synthesizes a lo-fi background beat purely with ffmpeg sine sources —
no external sample files needed."""
import subprocess
from dataclasses import dataclass

from app.infrastructure.ffmpeg_locator import FFmpegLocator

_BEAT_FILTERGRAPH = (
    "sine=frequency=60:sample_rate=44100,"
    "volume=0.18[kick];"
    "sine=frequency=8000:sample_rate=44100,"
    "volume=0.04[hat];"
    "sine=frequency=80:sample_rate=44100,"
    "volume=0.12[bass];"
    "[kick][hat][bass]amix=inputs=3:duration=longest,"
    "atrim=0:{duration:.2f},"
    "aecho=0.8:0.88:60:0.4,"
    "volume=0.55"
)


@dataclass
class MusicGenerator:
    ffmpeg: FFmpegLocator

    def generate(self, duration: float, output_path: str) -> bool:
        ffmpeg_exe = self.ffmpeg.ffmpeg_exe()
        beat = _BEAT_FILTERGRAPH.format(duration=duration)
        cmd = [
            ffmpeg_exe, "-f", "lavfi", "-i", beat,
            "-c:a", "aac", "-b:a", "96k", "-ac", "1",
            output_path, "-y", "-loglevel", "error",
        ]
        result = subprocess.run(cmd)
        return result.returncode == 0
