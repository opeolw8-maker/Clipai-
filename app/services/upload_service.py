"""Validates and saves an uploaded video file to the upload folder."""
import os
from dataclasses import dataclass

from werkzeug.datastructures import FileStorage

from app.config import Config


class UploadValidationError(Exception):
    """Raised for any user-facing upload problem (bad file, too small, etc.)."""


@dataclass
class UploadService:
    config: Config

    def save(self, file: FileStorage, job_id: str) -> str:
        ext = os.path.splitext(file.filename or "")[1].lower() or self.config.default_video_extension
        if ext not in self.config.allowed_video_extensions:
            ext = self.config.default_video_extension

        video_path = os.path.join(self.config.upload_folder, f"{job_id}{ext}")
        os.makedirs(self.config.upload_folder, exist_ok=True)
        file.save(video_path)

        if not os.path.exists(video_path) or os.path.getsize(video_path) < self.config.min_upload_size_bytes:
            raise UploadValidationError("File upload failed or file is too small. Please try again.")

        return video_path
