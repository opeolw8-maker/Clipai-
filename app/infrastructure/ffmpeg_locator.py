"""
Resolves the ffmpeg / ffprobe executables on this machine.
"""
import os
import subprocess
from functools import lru_cache
from typing import Optional


class FFmpegLocator:
    @staticmethod
    @lru_cache(maxsize=1)
    def ffmpeg_exe() -> str:
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return "ffmpeg"

    @staticmethod
    @lru_cache(maxsize=1)
    def ffprobe_exe() -> Optional[str]:
        try:
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            ffprobe_path = ffmpeg_path.replace("ffmpeg", "ffprobe")
            if os.path.exists(ffprobe_path):
                return ffprobe_path
            result = subprocess.run(["which", "ffprobe"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None
