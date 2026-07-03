"""
Transcribes audio with OpenAI Whisper ("tiny" model — fast, low RAM).
"""
from dataclasses import dataclass
from typing import List

from app.config import Config
from app.domain.models import TranscriptSegment


@dataclass
class TranscriptionService:
    config: Config

    def transcribe(self, audio_path: str) -> List[TranscriptSegment]:
        try:
            import whisper
            model = whisper.load_model(self.config.whisper_model_name)
            result = model.transcribe(audio_path, word_timestamps=True, fp16=False)
            return [
                TranscriptSegment(start=seg["start"], end=seg["end"], text=seg["text"].strip())
                for seg in result.get("segments", [])
            ]
        except Exception:
            return []
