"""Scraper source fetcher (docs/05 §1, type=scraper).

Stub / minimal viable implementation. For sites without RSS we call an
*external scraper actor* (e.g. a hosted scraping API) that returns normalized
JSON, then map fields -- we do NOT scrape HTML in-process.

Configuration lives in ``sources.meta`` (jsonb)::

    {
      "endpoint": "https://scraper.example.com/run",   # actor endpoint
      "method": "POST",
      "headers": {"Authorization": "Bearer ..."},
      "body": {"url": "https://site.example/news"},     # actor params
      "items_path": "results",
      "field_map": { "url": "url", "title": "title", ... }
    }

When not configured the fetcher logs "not configured" and returns [].
The field-mapping machinery is shared with the API fetcher; to support a
specific actor, subclass and override ``_extract_items`` / ``_map_item``.
"""
from __future__ import annotations

import logging

from app.ingestion.api_source import ApiSourceFetcher
from app.ingestion.base import RawArticle

logger = logging.getLogger(__name__)


class ScraperSourceFetcher(ApiSourceFetcher):
    """Calls an external scraper actor and maps the normalized JSON result."""

    def fetch(self, source) -> list[RawArticle]:
        config = (source.meta or {}).get("scraper", source.meta or {})
        endpoint = config.get("endpoint")
        field_map = config.get("field_map")
        if not endpoint or not field_map:
            logger.info(
                "Scraper source %s (%s) not configured (missing endpoint/field_map in meta); skipping",
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
        logger.info("Scraper source %s (%s): %d items mapped", source.id, source.name, len(articles))
        return articles
