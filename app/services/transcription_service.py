"""
Transcribes audio with faster-whisper ("tiny" model, int8 quantized) —
much lower memory footprint than openai-whisper's full PyTorch backend,
which is what pushed the app over Render's free-tier 512MB RAM limit.
The model is loaded once per process and reused across jobs, instead of
reloading it on every single transcription call.
"""
from dataclasses import dataclass
from typing import List

from app.config import Config
from app.domain.models import TranscriptSegment

_model = None  # loaded lazily once per process, reused across jobs


def _get_model(model_name: str):
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(model_name, device="cpu", compute_type="int8")
    return _model


@dataclass
class TranscriptionService:
    config: Config

    def transcribe(self, audio_path: str) -> List[TranscriptSegment]:
        try:
            model = _get_model(self.config.whisper_model_name)
            segments, _info = model.transcribe(audio_path, word_timestamps=False)
            return [
                TranscriptSegment(start=seg.start, end=seg.end, text=seg.text.strip())
                for seg in segments
            ]
        except Exception:
            return []
