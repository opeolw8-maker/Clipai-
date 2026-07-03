"""
Turns transcript segments (or, failing that, an AI guess) into an .srt
file for a specific clip window, plus the ffmpeg `subtitles` filter
styling presets used to burn them into video.
"""
from dataclasses import dataclass
from typing import List, Optional

from app.domain.models import TranscriptSegment
from app.infrastructure.llm_client import LLMClient

CAPTION_STYLES = {
    "classic": "FontSize=22,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2,Bold=0,Alignment=2",
    "bold": "FontSize=28,PrimaryColour=&H00ffff00,OutlineColour=&H000000,Outline=3,Bold=1,Alignment=2",
    "tiktok": "FontSize=26,PrimaryColour=&Hffffff,BackColour=&H800000ff,BorderStyle=4,Outline=0,Bold=1,Alignment=2",
    "minimal": "FontSize=16,PrimaryColour=&Hccffffff,OutlineColour=&H000000,Outline=1,Bold=0,Alignment=2",
    "fire": "FontSize=26,PrimaryColour=&H0045a5f9,OutlineColour=&H00000000,Outline=3,Bold=1,Alignment=2",
    "neon": "FontSize=26,PrimaryColour=&H00fa8bdb,OutlineColour=&H00000000,Outline=3,Bold=1,Alignment=2",
}
DEFAULT_CAPTION_STYLE = "classic"


def resolve_caption_style(style_name: str) -> str:
    return CAPTION_STYLES.get(style_name, CAPTION_STYLES[DEFAULT_CAPTION_STYLE])


def _format_timestamp(t: float) -> str:
    t = max(0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def segments_to_srt(segments: List[TranscriptSegment], clip_start: float) -> Optional[str]:
    """Convert Whisper segments (absolute timestamps) to SRT for a clip window."""
    lines = []
    idx = 1
    for seg in segments:
        rel_start = seg.start - clip_start
        rel_end = seg.end - clip_start
        if rel_end <= 0 or rel_start < 0:
            continue
        lines.append(f"{idx}\n{_format_timestamp(rel_start)} --> {_format_timestamp(rel_end)}\n{seg.text}\n")
        idx += 1
    return "\n".join(lines) if lines else None


@dataclass
class CaptionGenerator:
    llm_client: LLMClient

    def generate_srt(
        self,
        start: float,
        end: float,
        transcript_segments: Optional[List[TranscriptSegment]] = None,
    ) -> Optional[str]:
        """Prefer real Whisper segments for this clip window; fall back to
        an AI-generated placeholder transcript if none are available."""
        if transcript_segments:
            clip_segments = [s for s in transcript_segments if s.end > start and s.start < end]
            if clip_segments:
                return segments_to_srt(clip_segments, start)

        return self._generate_fallback_srt(end - start)

    def _generate_fallback_srt(self, clip_duration: float) -> Optional[str]:
        prompt = f"""Generate realistic subtitle/caption entries for a {clip_duration:.0f} second video clip.
Create 6-10 short caption lines that would appear during the clip.
Return ONLY a valid SRT format, nothing else. Example:
1
00:00:00,000 --> 00:00:03,000
This is the first caption line

2
00:00:03,500 --> 00:00:06,000
This is the second line"""
        try:
            return self.llm_client.complete(prompt, max_tokens=500, timeout=15)
        except Exception:
            return None
