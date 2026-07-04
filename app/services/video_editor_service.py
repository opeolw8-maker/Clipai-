"""
Cuts a single clip out of the source video and applies every requested
transformation: 9:16 reframe, mirror, color grade, speed/pitch shift,
background music mix, burned-in captions, and the watermark.
"""
import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from app.domain.models import ClipRequest, TranscriptSegment
from app.infrastructure.ffmpeg_locator import FFmpegLocator
from app.infrastructure.logo_asset import LogoAsset
from app.services.caption_service import CaptionGenerator, resolve_caption_style
from app.services.media_probe import MediaProbe
from app.services.music_service import MusicGenerator


@dataclass
class VideoEditor:
    ffmpeg: FFmpegLocator
    media_probe: MediaProbe
    music_generator: MusicGenerator
    caption_generator: CaptionGenerator
    logo_asset: LogoAsset

    def cut(
        self,
        video_path: str,
        start: float,
        end: float,
        output_path: str,
        options: ClipRequest,
        transcript_segments: Optional[List[TranscriptSegment]] = None,
    ) -> None:
        duration = end - start
        width, height = self.media_probe.get_dimensions(video_path)
        tmp_output = output_path.replace(".mp4", "_tmp.mp4")

        self._cut_and_process(video_path, start, duration, width, height, options, tmp_output)

        if options.add_music:
            self._mix_background_music(tmp_output, duration, output_path)

        if options.add_captions:
            self._burn_captions(tmp_output, output_path, start, end, options.caption_style, transcript_segments)

        self._apply_watermark(tmp_output, output_path)

    def _build_video_filters(self, width: int, height: int, options: ClipRequest) -> str:
        filters = []
        if options.do_reframe:
            if width > height:
                new_width = int(height * 9 / 16)
                x = (width - new_width) // 2
                filters.append(f"crop={new_width}:{height}:{x}:0")
            else:
                new_height = int(width * 16 / 9)
                y = max(0, (height - new_height) // 2)
                filters.append(f"crop={width}:{new_height}:0:{y}")
            filters.append("scale=720:1280")
        else:
            filters.append("scale=720:1280")

        if options.do_mirror:
            filters.append("hflip")
        if options.do_colorgrade:
            filters.append("eq=brightness=0.03:contrast=1.05:saturation=1.1")
        if options.do_speed:
            filters.append("setpts=0.99*PTS")

        return ",".join(filters)

    @staticmethod
    def _build_audio_filters(options: ClipRequest) -> List[str]:
        filters = []
        if options.do_pitch:
            filters.append("asetrate=44100*1.02,aresample=44100")
        if options.do_speed:
            filters.append("atempo=1.01")
        return filters

    def _cut_and_process(self, video_path, start, duration, width, height, options, tmp_output) -> None:
        ffmpeg_exe = self.ffmpeg.ffmpeg_exe()
        video_filter = self._build_video_filters(width, height, options)
        audio_filters = self._build_audio_filters(options)

        cmd = [ffmpeg_exe, "-ss", str(start), "-i", video_path, "-t", str(duration)]
        if video_filter:
            cmd += ["-vf", video_filter]
        if audio_filters:
            cmd += ["-af", ",".join(audio_filters)]
        cmd += [
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-vb", "1000k", "-c:a", "aac", "-b:a", "96k", "-ac", "1",
            "-movflags", "+faststart", "-threads", "1",
            tmp_output, "-y", "-loglevel", "error",
        ]
        subprocess.run(cmd, check=True)

    def _mix_background_music(self, tmp_output: str, duration: float, output_path: str) -> None:
        ffmpeg_exe = self.ffmpeg.ffmpeg_exe()
        music_path = output_path.replace(".mp4", "_music.aac")
        music_ok = self.music_generator.generate(duration, music_path)
        if not (music_ok and os.path.exists(music_path)):
            return
        try:
            music_mixed = output_path.replace(".mp4", "_musicmix.mp4")
            mix_cmd = [
                ffmpeg_exe, "-i", tmp_output, "-i", music_path,
                "-filter_complex",
                "[0:a]volume=1.0[orig];[1:a]volume=0.30[bg];[orig][bg]amix=inputs=2:duration=first[aout]",
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "96k",
                music_mixed, "-y", "-loglevel", "error",
            ]
            result = subprocess.run(mix_cmd)
            if result.returncode == 0:
                os.replace(music_mixed, tmp_output)
        except Exception:
            pass
        finally:
            try:
                os.remove(music_path)
            except Exception:
                pass

    def _burn_captions(
        self,
        tmp_output: str,
        output_path: str,
        start: float,
        end: float,
        caption_style: str,
        transcript_segments: Optional[List[TranscriptSegment]],
    ) -> None:
        ffmpeg_exe = self.ffmpeg.ffmpeg_exe()
        try:
            srt_path = output_path.replace(".mp4", ".srt")
            srt_content = self.caption_generator.generate_srt(start, end, transcript_segments)
            if not srt_content:
                return
            with open(srt_path, "w") as f:
                f.write(srt_content)

            captioned = output_path.replace(".mp4", "_cap.mp4")
            style_str = resolve_caption_style(caption_style)
            cap_cmd = [
                ffmpeg_exe, "-i", tmp_output,
                "-vf", f"subtitles={srt_path}:force_style='{style_str}'",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-c:a", "copy", "-threads", "1",
                captioned, "-y", "-loglevel", "error",
            ]
            result = subprocess.run(cap_cmd)
            if result.returncode == 0:
                os.replace(captioned, tmp_output)
            try:
                os.remove(srt_path)
            except Exception:
                pass
        except Exception:
            pass

    def _apply_watermark(self, tmp_output: str, output_path: str) -> None:
        ffmpeg_exe = self.ffmpeg.ffmpeg_exe()
        logo_path = self.logo_asset.path()
        if not os.path.exists(logo_path):
            os.rename(tmp_output, output_path)
            return
        try:
            logo_filter = (
                "[1:v]scale=140:-1,format=rgba,colorchannelmixer=aa=0.7[wm];"
                "[0:v][wm]overlay=W-w-15:H-h-15[out]"
            )
            cmd = [
                ffmpeg_exe, "-i", tmp_output, "-i", logo_path,
                "-filter_complex", logo_filter, "-map", "[out]", "-map", "0:a?",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-c:a", "aac", "-b:a", "96k",
                "-movflags", "+faststart", "-threads", "1",
                output_path, "-y", "-loglevel", "error",
            ]
            subprocess.run(cmd, check=True)
            os.remove(tmp_output)
        except Exception:
            os.rename(tmp_output, output_path)
