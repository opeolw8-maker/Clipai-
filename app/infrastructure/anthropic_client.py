"""
Anthropic Messages API client — an alternate LLMClient implementation.
"""
from __future__ import annotations

import json
import urllib.request as ur
from dataclasses import dataclass

from app.config import Config
from app.infrastructure.llm_client import LLMClient, LLMError

_API_VERSION = "2023-06-01"


class AnthropicError(LLMError):
    pass


@dataclass
class AnthropicClient(LLMClient):
    config: Config

    def complete(self, prompt: str, max_tokens: int = 1000, timeout: int = 30) -> str:
        if not self.config.anthropic_api_key:
            raise AnthropicError("ANTHROPIC_API_KEY not set")

        payload = json.dumps({
            "model": self.config.anthropic_model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()

        request = ur.Request(
            self.config.anthropic_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.config.anthropic_api_key,
                "anthropic-version": _API_VERSION,
            },
        )
        try:
            with ur.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read())
        except ur.HTTPError as e:
            body = e.read().decode()
            raise AnthropicError(f"Anthropic API error {e.code}: {body[:300]}") from e

        blocks = result.get("content", [])
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        if not text:
            raise AnthropicError(f"Anthropic response had no text content: {str(result)[:300]}")
        return text.strip()
