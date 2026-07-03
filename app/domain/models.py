"""
Domain models: plain data structures with no Flask, ffmpeg, or HTTP
dependencies. This is the innermost layer of the architecture.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional  # noqa: F401


class JobStatus(str, Enum):
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class JobStep(str, Enum):
    UPLOAD = "upload"
    AUDIO = "audio"
    TRANSCRIBE = "transcribe"
    ANALYZE = "analyze"
    CLIPS = "clips"
    CAPTIONS = "captions"
    DONE = "done"


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass
class ClipRequest:
    """Everything the user configured on the upload form, fully validated
    and typed."""
    num_clips: int = 5
    clip_length: int = 60
    topic: str = "general"
    cp_level: str = "none"
    add_captions: bool = True
    caption_style: str = "classic"
    do_reframe: bool = True
    do_mirror: bool = False
    do_colorgrade: bool = False
    do_speed: bool = False
    do_pitch: bool = False
    add_music: bool = False

    @property
    def protection_labels(self) -> List[str]:
        labels = []
        if self.do_mirror:
            labels.append("🔄 Mirrored")
        if self.do_colorgrade:
            labels.append("🎨 Color graded")
        if self.do_speed:
            labels.append("⚡ Speed adjusted")
        if self.do_pitch:
            labels.append("🎵 Pitch shifted")
        if self.add_music:
            labels.append("🎶 Music added")
        return labels


@dataclass
class ClipPlan:
    """A single clip as proposed by the AI analysis step, before it is cut."""
    title: Optional[str]
    description: str
    start: float
    end: float
    virality_score: int = 70
    reason: str = ""


@dataclass
class ClipResult:
    """A single finished, downloadable clip — what the frontend renders."""
    filename: str
    title: str
    description: str
    virality_score: int
    reason: str
    duration: int
    has_captions: bool
    protections: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "title": self.title,
            "description": self.description,
            "virality_score": self.virality_score,
            "reason": self.reason,
            "duration": self.duration,
            "has_captions": self.has_captions,
            "protections": self.protections,
        }


@dataclass
class Job:
    job_id: str
    status: JobStatus = JobStatus.RUNNING
    step: JobStep = JobStep.AUDIO
    clips: List[ClipResult] = field(default_factory=list)
    error_step: Optional[str] = None
    message: Optional[str] = None

    def to_dict(self) -> dict:
        data = {
            "status": self.status.value,
            "step": self.step.value if isinstance(self.step, JobStep) else self.step,
            "clips": [c.to_dict() for c in self.clips],
        }
        if self.error_step is not None:
            data["error_step"] = self.error_step
        if self.message is not None:
            data["message"] = self.message
        return data
