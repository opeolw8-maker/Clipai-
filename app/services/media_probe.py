"""
Reads facts about a video file (duration, dimensions) via ffprobe, with
ffmpeg-stderr-parsing fallbacks for environments where ffprobe is missing.
"""
import os
import re
import subprocess
from dataclasses import dataclass

from app.infrastructure.ffmpeg_locator import FFmpegLocator


@dataclass
class MediaProbe:
    ffmpeg: FFmpegLocator

    def get_duration(self, path: str) -> float:
        ffmpeg_exe = self.ffmpeg.ffmpeg_exe()
        ffprobe_exe = self.ffmpeg.ffprobe_exe()

        if ffprobe_exe:
            try:
                result = subprocess.run(
                    [ffprobe_exe, "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", path],
                    capture_output=True, text=True, timeout=15,
                )
                value = result.stdout.strip()
                if value:
                    return float(value)
            except Exception:
                pass

        duration = self._duration_from_ffmpeg_probe(ffmpeg_exe, path, timeout=30)
        if duration is not None:
            return duration

        duration = self._duration_from_ffmpeg_probe(ffmpeg_exe, path, timeout=15, decode=False)
        if duration is not None:
            return duration

        try:
            file_size = os.path.getsize(path) if os.path.exists(path) else -1
            debug_result = subprocess.run([ffmpeg_exe, "-i", path], capture_output=True, text=True, timeout=10)
            debug = (debug_result.stdout + debug_result.stderr)[:300]
        except Exception as probe_error:
            file_size = -1
            debug = str(probe_error)
        raise Exception(
            f"Could not get video duration — file size: {file_size} bytes, ffmpeg output: {debug}"
        )

    @staticmethod
    def _duration_from_ffmpeg_probe(ffmpeg_exe: str, path: str, timeout: int, decode: bool = True):
        try:
            cmd = [ffmpeg_exe, "-i", path]
            if decode:
                cmd += ["-f", "null", "-"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            combined = result.stdout + result.stderr
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", combined)
            if match:
                h, m, s = float(match.group(1)), float(match.group(2)), float(match.group(3))
                return h * 3600 + m * 60 + s
        except Exception:
            pass
        return None

    def get_dimensions(self, path: str) -> tuple[int, int]:
        ffmpeg_exe = self.ffmpeg.ffmpeg_exe()
        ffprobe_exe = self.ffmpeg.ffprobe_exe()

        if ffprobe_exe:
            result = subprocess.run(
                [ffprobe_exe, "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
                capture_output=True, text=True,
            )
            dims = result.stdout.strip().split(",")
            return int(dims[0]), int(dims[1])

        result = subprocess.run([ffmpeg_exe, "-i", path], capture_output=True, text=True)
        match = re.search(r"(\d{2,4})x(\d{2,4})", result.stderr)
        if match:
            return int(match.group(1)), int(match.group(2))
        return 1920, 1080
