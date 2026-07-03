"""
Composition root.

Every other module receives its dependencies through its constructor
(constructor injection) instead of reaching for globals or doing its own
`import os; os.environ.get(...)`. This module is the one place that
actually instantiates concrete classes and wires them together.
"""
from dataclasses import dataclass

from app.config import Config, get_config
from app.domain.job_repository import InMemoryJobRepository, JobRepository, RedisJobRepository
from app.infrastructure.anthropic_client import AnthropicClient
from app.infrastructure.ffmpeg_locator import FFmpegLocator
from app.infrastructure.llm_client import LLMClient
from app.infrastructure.logo_asset import LogoAsset
from app.infrastructure.openrouter_client import OpenRouterClient
from app.services.ai_analysis_service import AIClipAnalyzer
from app.services.audio_service import AudioExtractor
from app.services.caption_service import CaptionGenerator
from app.services.clip_pipeline import ClipPipeline
from app.services.job_executor import JobExecutor
from app.services.media_probe import MediaProbe
from app.services.music_service import MusicGenerator
from app.services.transcription_service import TranscriptionService
from app.services.upload_service import UploadService
from app.services.video_editor_service import VideoEditor


@dataclass
class Container:
    config: Config
    jobs: JobRepository
    upload_service: UploadService
    job_executor: object  # JobExecutor | CeleryJobExecutor — same `.submit(...)` interface


def build_job_repository(config: Config) -> JobRepository:
    """Selects the job-storage backend. Defaults to the original
    in-memory behavior; set JOB_BACKEND=redis to persist jobs across
    restarts / share them across processes. See .env.example."""
    if config.job_backend == "redis":
        return RedisJobRepository(redis_url=config.redis_url)
    return InMemoryJobRepository()


def build_llm_client(config: Config) -> LLMClient:
    """Selects which LLM provider AIClipAnalyzer/CaptionGenerator talk to.
    Defaults to the original OpenRouter behavior; set LLM_PROVIDER=anthropic
    (+ ANTHROPIC_API_KEY) to use Claude directly instead. See .env.example."""
    if config.llm_provider == "anthropic":
        return AnthropicClient(config=config)
    return OpenRouterClient(config=config)


def build_pipeline(config: Config, jobs: JobRepository) -> ClipPipeline:
    """Wires every service that makes up the ClipPipeline use-case."""
    ffmpeg = FFmpegLocator()
    llm_client = build_llm_client(config)

    media_probe = MediaProbe(ffmpeg=ffmpeg)
    audio_extractor = AudioExtractor(ffmpeg=ffmpeg)
    transcription_service = TranscriptionService(config=config)
    ai_analyzer = AIClipAnalyzer(llm_client=llm_client)
    music_generator = MusicGenerator(ffmpeg=ffmpeg)
    caption_generator = CaptionGenerator(llm_client=llm_client)
    logo_asset = LogoAsset()
    video_editor = VideoEditor(
        ffmpeg=ffmpeg,
        media_probe=media_probe,
        music_generator=music_generator,
        caption_generator=caption_generator,
        logo_asset=logo_asset,
    )
    return ClipPipeline(
        jobs=jobs,
        media_probe=media_probe,
        audio_extractor=audio_extractor,
        transcription_service=transcription_service,
        ai_analyzer=ai_analyzer,
        video_editor=video_editor,
    )


def build_job_executor(config: Config, pipeline: ClipPipeline):
    """Selects the job-execution backend. Defaults to the original
    per-request daemon thread; set EXECUTOR_BACKEND=celery to run jobs on
    a real Celery worker fleet instead."""
    if config.executor_backend == "celery":
        from app.services.celery_tasks import CeleryJobExecutor
        return CeleryJobExecutor()
    return JobExecutor(pipeline=pipeline)


def build_container(config: Config = None) -> Container:
    config = config or get_config()
    config.ensure_directories()

    if config.executor_backend == "celery" and config.job_backend != "redis":
        import warnings
        warnings.warn(
            "EXECUTOR_BACKEND=celery requires JOB_BACKEND=redis (or another "
            "shared backend) — with the in-memory repository, the web "
            "process and the Celery worker each have their own copy of "
            "job state and /status will never see the worker's updates.",
            RuntimeWarning,
        )

    jobs = build_job_repository(config)
    pipeline = build_pipeline(config, jobs)
    job_executor = build_job_executor(config, pipeline)
    upload_service = UploadService(config=config)

    return Container(
        config=config,
        jobs=jobs,
        upload_service=upload_service,
        job_executor=job_executor,
)
