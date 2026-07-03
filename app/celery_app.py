"""
Celery application factory.

This module is only imported when `EXECUTOR_BACKEND=celery` (see
app/container.py).

Run a worker with:
    celery -A app.celery_app.celery_app worker --loglevel=info
"""
from celery import Celery

from app.config import Config


def build_celery_app(config: Config) -> Celery:
    celery_app = Celery(
        "clipai",
        broker=config.celery_broker_url,
        backend=config.celery_broker_url,
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        broker_transport_options={"visibility_timeout": 3600},
        task_track_started=True,
    )
    return celery_app
