"""
Asks an LLM (via OpenRouter) to pick the best clip-worthy moments from a
video, using the real transcript when available and falling back to a
duration-only guess otherwise.
"""
import json
import re
from dataclasses import dataclass
from typing import List, Optional

from app.domain.models import ClipPlan, TranscriptSegment
from app.infrastructure.llm_client import LLMClient, LLMError

TOPIC_PROMPTS = {
    "general": "the most engaging and interesting moments",
    "funny": "the funniest and most humorous moments",
    "emotional": "the most emotional and touching moments",
    "educational": "the most informative and educational moments",
    "motivational": "the most inspiring and motivational moments",
    "shocking": "the most surprising and shocking moments",
}


class AIAnalysisError(Exception):
    pass


@dataclass
class AIClipAnalyzer:
    llm_client: LLMClient

    def analyze(
        self,
        duration: float,
        num_clips: int,
        clip_length: int,
        topic: str,
        transcript_segments: Optional[List[TranscriptSegment]] = None,
    ) -> List[ClipPlan]:
        focus = TOPIC_PROMPTS.get(topic, TOPIC_PROMPTS["general"])
        prompt = self._build_prompt(duration, num_clips, clip_length, focus, transcript_segments)

        try:
            raw_text = self.llm_client.complete(prompt, max_tokens=1500, timeout=30)
        except LLMError:
            raise
        except Exception as e:
            raise AIAnalysisError(str(e)) from e

        clips_data = self._parse_json_array(raw_text)
        return [
            ClipPlan(
                title=c.get("title"),
                description=c.get("description", ""),
                start=c["start"],
                end=c["end"],
                virality_score=c.get("virality_score", 70),
                reason=c.get("reason", ""),
            )
            for c in clips_data
        ]

    @staticmethod
    def _build_prompt(
        duration: float,
        num_clips: int,
        clip_length: int,
        focus: str,
        transcript_segments: Optional[List[TranscriptSegment]],
    ) -> str:
        if transcript_segments:
            full_text = ""
            for seg in transcript_segments:
                full_text += f"[{seg.start:.1f}s] {seg.text}\n"
            full_text = full_text[:3000]
            return f"""Here is a real transcript of a video ({duration:.0f} seconds long) with timestamps:

{full_text}

Find {num_clips} clips focusing on {focus}, each ~{clip_length} seconds long.
Use the actual transcript to identify the best moments based on real content and what was said.

Return ONLY a valid JSON array with NO extra text before or after:
[{{"title":"Catchy short title","description":"2-3 sentence social media description with hashtags at the end.","start":0,"end":{clip_length},"virality_score":85,"reason":"Why this moment is viral"}}]

Rules: use real timestamps from the transcript, never exceed {duration:.0f}s, no overlaps, each clip ~{clip_length}s."""

        return f"""A video is {duration:.0f} seconds long. Find {num_clips} clips focusing on {focus}, each ~{clip_length} seconds.

Return ONLY a valid JSON array with NO extra text before or after:
[{{"title":"Catchy short title","description":"2-3 sentence social media description with hashtags at the end.","start":0,"end":{clip_length},"virality_score":80,"reason":"Why this clip is viral"}}]

Rules: never exceed {duration:.0f}s, no overlaps, each clip ~{clip_length}s."""

    @staticmethod
    def _parse_json_array(text: str) -> list:
        text = re.sub(r"```json\s*|\s*```", "", text).strip()
        start_idx = text.find("[")
        end_idx = text.rfind("]")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            text = text[start_idx:end_idx + 1]
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise AIAnalysisError(f"AI returned invalid JSON: {str(e)} — raw: {text[:300]}") from e
