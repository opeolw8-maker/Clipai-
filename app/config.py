"""
Centralized application configuration.

All environment-dependent values (paths, API keys, tunables) live here.
Nothing else in the codebase should call os.environ.get(...) directly —
that keeps configuration concerns out of business logic and makes the
app trivially testable (swap a Config instance instead of monkeypatching env).
"""
import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class Config:
    upload_folder: str = "/tmp/uploads"
    output_folder: str = "/tmp/outputs"
    port: int = int(os.environ.get("PORT", 8080))
    openrouter_api_key: str = os.environ.get("OPENROUTER_API_KEY", "")
    openrouter_url: str = "https://openrouter.ai/api/v1/chat/completions"
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct"
    openrouter_referer: str = "https://clipai.app"
    openrouter_title: str = "ClipAI"

    llm_provider: str = os.environ.get("LLM_PROVIDER", "openrouter")  # "openrouter" | "anthropic"
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    anthropic_url: str = "https://api.anthropic.com/v1/messages"
    anthropic_model: str = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

    allowed_video_extensions: tuple = (".mp4", ".mov", ".mkv", ".avi", ".webm")
    default_video_extension: str = ".mp4"
    min_upload_size_bytes: int = 1000

    whisper_model_name: str = "tiny"

    job_backend: str = os.environ.get("JOB_BACKEND", "memory")  # "memory" | "redis"
    redis_url: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    executor_backend: str = os.environ.get("EXECUTOR_BACKEND", "thread")  # "thread" | "celery"
    celery_broker_url: str = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")

    def ensure_directories(self) -> None:
        os.makedirs(self.upload_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)


def get_config() -> Config:
    """Factory so tests can inject a different Config without touching env vars."""
    return Config()
