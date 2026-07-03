"""
Job persistence, isolated behind a small repository interface.
"""
from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Optional

from app.domain.models import Job, JobStatus, JobStep


class JobRepository(ABC):
    @abstractmethod
    def create(self, job_id: str) -> Job:
        ...

    @abstractmethod
    def get(self, job_id: str) -> Optional[Job]:
        ...

    @abstractmethod
    def update_step(self, job_id: str, step: JobStep) -> None:
        ...

    @abstractmethod
    def mark_done(self, job_id: str, clips: list) -> None:
        ...

    @abstractmethod
    def mark_error(self, job_id: str, error_step: str, message: str) -> None:
        ...


class InMemoryJobRepository(JobRepository):
    """Thread-safe in-memory job store."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, job_id: str) -> Job:
        job = Job(job_id=job_id, status=JobStatus.RUNNING, step=JobStep.AUDIO)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def update_step(self, job_id: str, step: JobStep) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.step = step

    def mark_done(self, job_id: str, clips: list) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.DONE
                job.step = JobStep.DONE
                job.clips = clips

    def mark_error(self, job_id: str, error_step: str, message: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.ERROR
                job.step = JobStep.DONE
                job.error_step = error_step
                job.message = message


class RedisJobRepository(JobRepository):
    """Redis-backed job store — the swap-in for InMemoryJobRepository once
    the app runs as more than one process."""

    _KEY_PREFIX = "clipai:job:"
    _TTL_SECONDS = 24 * 60 * 60

    def __init__(self, redis_url: str) -> None:
        try:
            import redis
        except ImportError as e:
            raise ImportError(
                "RedisJobRepository requires the 'redis' package. "
                "Install it with: pip install redis"
            ) from e
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def _key(self, job_id: str) -> str:
        return f"{self._KEY_PREFIX}{job_id}"

    def _read(self, job_id: str) -> Optional[Job]:
        raw = self._client.get(self._key(job_id))
        if raw is None:
            return None
        return self._deserialize(job_id, raw)

    def _write(self, job: Job) -> None:
        self._client.set(self._key(job.job_id), self._serialize(job), ex=self._TTL_SECONDS)

    @staticmethod
    def _serialize(job: Job) -> str:
        import json
        data = job.to_dict()
        data["job_id"] = job.job_id
        return json.dumps(data)

    @staticmethod
    def _deserialize(job_id: str, raw: str) -> Job:
        import json
        from app.domain.models import ClipResult
        data = json.loads(raw)
        job = Job(
            job_id=job_id,
            status=JobStatus(data["status"]),
            step=JobStep(data["step"]),
            error_step=data.get("error_step"),
            message=data.get("message"),
        )
        job.clips = [ClipResult(**c) for c in data.get("clips", [])]
        return job

    def create(self, job_id: str) -> Job:
        job = Job(job_id=job_id, status=JobStatus.RUNNING, step=JobStep.AUDIO)
        self._write(job)
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._read(job_id)

    def update_step(self, job_id: str, step: JobStep) -> None:
        job = self._read(job_id)
        if job:
            job.step = step
            self._write(job)

    def mark_done(self, job_id: str, clips: list) -> None:
        job = self._read(job_id)
        if job:
            job.status = JobStatus.DONE
            job.step = JobStep.DONE
            job.clips = clips
            self._write(job)

    def mark_error(self, job_id: str, error_step: str, message: str) -> None:
        job = self._read(job_id)
        if job:
            job.status = JobStatus.ERROR
            job.step = JobStep.DONE
            job.error_step = error_step
            job.message = message
            self._write(job)
