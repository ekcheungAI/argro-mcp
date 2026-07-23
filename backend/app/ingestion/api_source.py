"""JSON API source fetcher (docs/05 §1, type=api).

Stub / minimal viable implementation. The per-source configuration lives in
``sources.meta`` (jsonb), e.g.::

    {
      "endpoint": "https://api.example.com/v1/news",
      "method": "GET",                     # default GET
      "headers": {"Authorization": "Bearer ..."},
      "params": {"limit": 50},
      "items_path": "data.items",          # dotted path to the items array
      "field_map": {                       # RawArticle field -> dotted path in item
        "external_id": "id",
        "url": "url",
        "title": "headline",
        "summary": "abstract",
        "content": "body",
        "published_at": "published_at"
      }
    }

When ``endpoint`` / ``field_map`` are not configured the fetcher logs
"not configured" and returns [] -- this keeps the pipeline alive while a
partner API integration is pending. To extend: subclass and override
``_extract_items`` / ``_map_item``.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.ingestion.base import RawArticle

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20.0


def _dig(obj: Any, path: str | None) -> Any:
    """Resolve a dotted path (e.g. "data.items") against nested dicts/lists."""
    if not path:
        return None
    current = obj
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            current = current[idx] if idx < len(current) else None
        else:
            return None
        if current is None:
            return None
    return current


class ApiSourceFetcher:
    """Fetches a partner JSON API and maps fields per sources.meta config."""

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout

    def fetch(self, source) -> list[RawArticle]:
        config = (source.meta or {}).get("api", source.meta or {})
        endpoint = config.get("endpoint") or source.feed_url
        field_map = config.get("field_map")
        if not endpoint or not field_map:
            logger.info(
                "API source %s (%s) not configured (missing endpoint/field_map in meta); skipping",
                source.id,
                source.name,
            )
            return []

        payload = self._call(source, endpoint, config)
        if payload is None:
            return []

        items = self._extract_items(payload, config)
        articles: list[RawArticle] = []
        for item in items:
            raw = self._map_item(source, item, field_map)
            if raw is not None:
                articles.append(raw)
        logger.info("API source %s (%s): %d items mapped", source.id, source.name, len(articles))
        return articles

    # ------------------------------------------------------------------ #
    # extension points
    # ------------------------------------------------------------------ #

    def _call(self, source, endpoint: str, config: dict) -> Any | None:
        method = (config.get("method") or "GET").upper()
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.request(
                    method,
                    endpoint,
                    headers=config.get("headers"),
                    params=config.get("params"),
                    json=config.get("body"),
                )
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("API source %s (%s) call failed: %s", source.id, source.name, exc)
            return None

    def _extract_items(self, payload: Any, config: dict) -> list:
        items = _dig(payload, config.get("items_path"))
        if items is None:
            items = payload
        if isinstance(items, list):
            return items
        logger.warning("API source items_path did not resolve to a list; got %r", type(items))
        return []

    def _map_item(self, source, item: Any, field_map: dict) -> RawArticle | None:
        url = _dig(item, field_map.get("url"))
        title = _dig(item, field_map.get("title"))
        if not url or not title:
            return None
        return RawArticle(
            source_id=source.id,
            external_id=_str_or_none(_dig(item, field_map.get("external_id"))),
            url=str(url),
            title=str(title),
            summary=_str_or_none(_dig(item, field_map.get("summary"))),
            content=_str_or_none(_dig(item, field_map.get("content"))),
            published_at=_str_or_none(_dig(item, field_map.get("published_at"))),
            metadata=config_metadata(item, field_map),
        )


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip() or None


def config_metadata(item: Any, field_map: dict) -> dict | None:
    """Optional extra fields, e.g. field_map: {"metadata.author": "byline"}."""
    meta: dict = {}
    for key, path in field_map.items():
        if key.startswith("metadata."):
            value = _dig(item, path)
            if value is not None:
                meta[key[len("metadata."):]] = value
    return meta or None
