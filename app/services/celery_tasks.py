"""
The Celery task wrapper around ClipPipeline. Only used when
EXECUTOR_BACKEND=celery.
"""
from dataclasses import asdict

from app.celery_app import build_celery_app
from app.config import get_config
from app.domain.models import ClipRequest

_config = get_config()
celery_app = build_celery_app(_config)

_pipeline = None  # built lazily, once per worker process


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        from app.container import build_job_repository, build_pipeline
        jobs = build_job_repository(_config)
        _pipeline = build_pipeline(_config, jobs)
    return _pipeline


@celery_app.task(name="clipai.run_clip_pipeline", bind=True, max_retries=0)
def run_clip_pipeline_task(self, job_id: str, video_path: str, job_dir: str, options_dict: dict) -> None:
    options = ClipRequest(**options_dict)
    _get_pipeline().run(job_id, video_path, job_dir, options)


class CeleryJobExecutor:
    """Drop-in replacement for the thread-based JobExecutor."""

    def submit(self, job_id: str, video_path: str, job_dir: str, options: ClipRequest) -> None:
        run_clip_pipeline_task.delay(job_id, video_path, job_dir, asdict(options))
