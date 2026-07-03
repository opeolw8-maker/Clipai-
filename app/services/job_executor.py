"""
Runs the clip pipeline in a background thread so the /upload request can
return immediately with a job id.
"""
import threading
from dataclasses import dataclass

from app.domain.models import ClipRequest
from app.services.clip_pipeline import ClipPipeline


@dataclass
class JobExecutor:
    pipeline: ClipPipeline

    def submit(self, job_id: str, video_path: str, job_dir: str, options: ClipRequest) -> None:
        thread = threading.Thread(
            target=self.pipeline.run,
            args=(job_id, video_path, job_dir, options),
        )
        thread.daemon = True
        thread.start()
