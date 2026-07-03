"""
The ClipPipeline is the single use-case that ties every service
together: probe the video, extract audio, transcribe, ask the AI for
clip moments, cut+edit each one, and record results on the job.
"""
import os
from dataclasses import dataclass

from app.domain.job_repository import JobRepository
from app.domain.models import ClipRequest, ClipResult, JobStep
from app.services.ai_analysis_service import AIClipAnalyzer
from app.services.audio_service import AudioExtractor
from app.services.media_probe import MediaProbe
from app.services.transcription_service import TranscriptionService
from app.services.video_editor_service import VideoEditor


@dataclass
class ClipPipeline:
    jobs: JobRepository
    media_probe: MediaProbe
    audio_extractor: AudioExtractor
    transcription_service: TranscriptionService
    ai_analyzer: AIClipAnalyzer
    video_editor: VideoEditor

    def run(self, job_id: str, video_path: str, job_dir: str, options: ClipRequest) -> None:
        try:
            self._run(job_id, video_path, job_dir, options)
        except Exception as e:
            job = self.jobs.get(job_id)
            error_step = job.step.value if job else "clips"
            self.jobs.mark_error(job_id, error_step=error_step, message=str(e))

    def _run(self, job_id: str, video_path: str, job_dir: str, options: ClipRequest) -> None:
        duration = self.media_probe.get_duration(video_path)

        self.jobs.update_step(job_id, JobStep.AUDIO)
        audio_path = os.path.join(job_dir, "audio.wav")
        self.audio_extractor.extract(video_path, audio_path)

        self.jobs.update_step(job_id, JobStep.TRANSCRIBE)
        transcript_segments = self.transcription_service.transcribe(audio_path)

        self.jobs.update_step(job_id, JobStep.ANALYZE)
        clip_plans = self.ai_analyzer.analyze(
            duration, options.num_clips, options.clip_length, options.topic, transcript_segments,
        )

        self.jobs.update_step(job_id, JobStep.CLIPS)
        results = self._cut_all_clips(
            video_path, job_dir, clip_plans, options, duration, transcript_segments, job_id,
        )

        results.sort(key=lambda c: c.virality_score, reverse=True)
        self.jobs.mark_done(job_id, results)
        self._cleanup(audio_path, video_path)

    def _cut_all_clips(self, video_path, job_dir, clip_plans, options, duration,
                        transcript_segments, job_id) -> list[ClipResult]:
        results: list[ClipResult] = []
        for i, plan in enumerate(clip_plans[:options.num_clips]):
            start = max(0, float(plan.start))
            end = min(duration, float(plan.end))
            if end - start < 5:
                end = min(duration, start + options.clip_length)

            filename = f"clip_{i + 1:02d}_score{plan.virality_score}.mp4"
            self.jobs.update_step(job_id, JobStep.CLIPS)
            self.video_editor.cut(
                video_path, start, end, os.path.join(job_dir, filename),
                options, transcript_segments=transcript_segments,
            )
            self.jobs.update_step(job_id, JobStep.CAPTIONS)

            results.append(ClipResult(
                filename=filename,
                title=plan.title if plan.title is not None else f"Clip {i + 1}",
                description=plan.description,
                virality_score=plan.virality_score,
                reason=plan.reason,
                duration=round(end - start),
                has_captions=options.add_captions,
                protections=options.protection_labels,
            ))
        return results

    @staticmethod
    def _cleanup(audio_path: str, video_path: str) -> None:
        for path in (audio_path, video_path):
            try:
                os.remove(path)
            except Exception:
                pass
