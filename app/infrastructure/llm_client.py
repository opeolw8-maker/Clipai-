"""
Provider-agnostic interface for "send a prompt, get text back".
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMError(Exception):
    """Base class for provider errors, so callers can catch one type
    regardless of which provider is configured."""


class LLMClient(ABC):
    @abstractmethod
    def complete(self, prompt: str, max_tokens: int = 1000, timeout: int = 30) -> str:
        """Send a single-turn completion request and return the raw
        assistant message text (no JSON envelope, no role wrapper)."""
        ...
