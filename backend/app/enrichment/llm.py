"""LLM provider interface + Moonshot (Kimi) implementation.

Design notes:
- ``LLMProvider`` protocol keeps the enrichment steps provider-agnostic;
  ``MoonshotClient`` is the concrete sync implementation (httpx).
- Without ``MOONSHOT_API_KEY`` the client reports ``available() == False``
  and every method returns None instead of raising, so all enrichment steps
  degrade to graceful no-ops.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Protocol, runtime_checkable

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60.0
DEFAULT_CHAT_MODEL = "kimi-k2"  # legacy fallback; primary default is settings.translation_model
DEFAULT_TEMPERATURE = 0.2


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal interface used by the enrichment steps."""

    def available(self) -> bool:
        """True when the provider is configured (API key present)."""
        ...

    def chat(self, prompt: str, model: str | None = None, **kwargs) -> str | None:
        """Single-turn chat completion; returns the assistant text or None."""
        ...

    def chat_json(self, prompt: str, model: str | None = None, **kwargs) -> Any | None:
        """Chat completion parsed as JSON; returns the parsed object or None."""
        ...

    def embed(self, texts: list[str], model: str | None = None) -> list[list[float]] | None:
        """Embeddings for a batch of texts, or None when unsupported/failed."""
        ...


class MoonshotClient:
    """Sync client for the Moonshot (Kimi) OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.moonshot_api_key
        self.base_url = (base_url or settings.moonshot_base_url).rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------ #
    # interface
    # ------------------------------------------------------------------ #

    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, prompt: str, model: str | None = None, **kwargs) -> str | None:
        if not self.available():
            logger.debug("Moonshot API key not set; skipping chat call")
            return None
        payload = {
            "model": model or settings.translation_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.pop("temperature", DEFAULT_TEMPERATURE),
            **kwargs,
        }
        data = self._post("/chat/completions", payload)
        if data is None:
            return None
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            logger.warning("Unexpected Moonshot chat response shape: %s", str(data)[:500])
            return None

    def chat_json(self, prompt: str, model: str | None = None, **kwargs) -> Any | None:
        """Ask for a JSON response and parse it tolerantly (strips ``` fences)."""
        text = self.chat(prompt, model=model, **kwargs)
        if text is None:
            return None
        return _parse_json(text)

    def embed(self, texts: list[str], model: str | None = None) -> list[list[float]] | None:
        """Call the OpenAI-compatible /embeddings endpoint.

        Moonshot's embedding support is limited/optional; any failure (HTTP
        error, unexpected shape) is logged and yields None so the caller can
        skip embedding-dependent steps.
        """
        if not self.available():
            logger.debug("Moonshot API key not set; skipping embed call")
            return None
        if not texts:
            return []
        payload = {"model": model or settings.embedding_model, "input": texts}
        base = (settings.embedding_base_url or self.base_url).rstrip("/")
        key = settings.embedding_api_key or self.api_key
        data = self._post("/embeddings", payload, base_url=base, api_key=key)
        if data is None:
            return None
        try:
            rows = sorted(data["data"], key=lambda d: d["index"])
            return [row["embedding"] for row in rows]
        except (KeyError, TypeError):
            logger.warning("Unexpected Moonshot embed response shape: %s", str(data)[:500])
            return None

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    def _post(self, path: str, payload: dict, base_url: str | None = None, api_key: str | None = None) -> dict | None:
        url = f"{(base_url or self.base_url)}{path}"
        headers = {
            "Authorization": f"Bearer {api_key or self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Moonshot %s returned HTTP %d: %s",
                path,
                exc.response.status_code,
                exc.response.text[:300],
            )
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Moonshot %s request failed: %s", path, exc)
        return None


def _parse_json(text: str) -> Any | None:
    """Parse JSON from an LLM reply, tolerating markdown code fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Strip ```json ... ``` fences.
        lines = cleaned.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Last resort: grab the outermost {...} or [...] block.
        for opener, closer in (("{", "}"), ("[", "]")):
            start = cleaned.find(opener)
            end = cleaned.rfind(closer)
            if start != -1 and end > start:
                try:
                    return json.loads(cleaned[start : end + 1])
                except json.JSONDecodeError:
                    continue
    logger.warning("Could not parse JSON from LLM reply: %s", text[:300])
    return None


# Shared default client (stateless aside from config).
_default_client: MoonshotClient | None = None


def get_client() -> MoonshotClient:
    """Return a shared MoonshotClient built from settings."""
    global _default_client
    if _default_client is None:
        _default_client = MoonshotClient()
    return _default_client
