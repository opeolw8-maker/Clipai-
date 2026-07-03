"""
OpenRouter chat-completions client — the default LLMClient implementation.
"""
from __future__ import annotations

import json
import urllib.request as ur
from dataclasses import dataclass

from app.config import Config
from app.infrastructure.llm_client import LLMClient, LLMError


class OpenRouterError(LLMError):
    pass


@dataclass
class OpenRouterClient(LLMClient):
    config: Config

    def complete(self, prompt: str, max_tokens: int = 1000, timeout: int = 30) -> str:
        if not self.config.openrouter_api_key:
            raise OpenRouterError("OPENROUTER_API_KEY not set in Railway Variables")

        payload = json.dumps({
            "model": self.config.openrouter_model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()

        request = ur.Request(
            self.config.openrouter_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.openrouter_api_key}",
                "HTTP-Referer": self.config.openrouter_referer,
                "X-Title": self.config.openrouter_title,
            },
        )
        try:
            with ur.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read())
        except ur.HTTPError as e:
            body = e.read().decode()
            raise OpenRouterError(f"OpenRouter API error {e.code}: {body[:300]}") from e

        return result["choices"][0]["message"]["content"].strip()
