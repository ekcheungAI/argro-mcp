"""RSS/Atom fetcher built on feedparser (docs/05 §2, type=rss).

Robust by contract: network errors, HTTP errors and malformed feeds are
logged and yield an empty list -- the ingestion pipeline must never crash
because one feed is down.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import feedparser
import httpx

from app.ingestion.base import RawArticle, strip_html

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20.0
USER_AGENT = "argro-mcp-ingester/0.1 (+https://github.com/argro-mcp)"


class RssFetcher:
    """Fetches an RSS/Atom feed and maps entries to RawArticle."""

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout

    def fetch(self, source) -> list[RawArticle]:
        if not source.feed_url:
            logger.warning("RSS source %s (%s) has no feed_url; skipping", source.id, source.name)
            return []

        content = self._download(source)
        if content is None:
            return []

        try:
            feed = feedparser.parse(content)
        except Exception:  # feedparser is lenient, but never trust the network
            logger.exception("Failed to parse feed for source %s (%s)", source.id, source.name)
            return []

        # bozo=1 signals a malformed feed; entries may still be usable.
        if getattr(feed, "bozo", 0) and not feed.entries:
            logger.warning(
                "Malformed feed with no entries for source %s (%s): %s",
                source.id,
                source.name,
                getattr(feed, "bozo_exception", "unknown error"),
            )
            return []

        articles: list[RawArticle] = []
        for entry in feed.entries:
            raw = self._entry_to_raw(source, entry)
            if raw is not None:
                articles.append(raw)
        logger.info("RSS source %s (%s): %d entries parsed", source.id, source.name, len(articles))
        return articles

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    def _download(self, source) -> bytes | None:
        """GET the feed with a timeout; None on any failure."""
        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                resp = client.get(source.feed_url)
        except httpx.TimeoutException:
            logger.warning("Timeout fetching feed %s (source %s)", source.feed_url, source.id)
            return None
        except httpx.HTTPError as exc:
            logger.warning("HTTP error fetching feed %s (source %s): %s", source.feed_url, source.id, exc)
            return None

        if resp.status_code != 200:
            logger.warning(
                "Feed %s (source %s) returned HTTP %d", source.feed_url, source.id, resp.status_code
            )
            return None
        return resp.content

    def _entry_to_raw(self, source, entry) -> RawArticle | None:
        url = (entry.get("link") or "").strip()
        title = strip_html(entry.get("title")) or ""
        if not url or not title:
            logger.debug("Skipping entry without link/title in source %s", source.id)
            return None

        summary = strip_html(entry.get("summary") or entry.get("description"))
        content = self._extract_content(entry)
        published_at = self._extract_published(entry)

        metadata: dict = {}
        author = entry.get("author") or entry.get("dc_creator")
        if author:
            metadata["author"] = author.strip()
        tags = [t.get("term") for t in entry.get("tags", []) if t.get("term")]
        if tags:
            metadata["tags"] = tags

        return RawArticle(
            source_id=source.id,
            external_id=(entry.get("id") or entry.get("guid") or "").strip() or None,
            url=url,
            title=title,
            summary=summary,
            content=content,
            published_at=published_at,
            metadata=metadata or None,
        )

    @staticmethod
    def _extract_content(entry) -> str | None:
        """Prefer entry.content[0].value, else use the summary as content."""
        contents = entry.get("content")
        if contents:
            value = contents[0].get("value")
            if value:
                return value.strip()
        return None

    @staticmethod
    def _extract_published(entry) -> datetime:
        """published_parsed / updated_parsed (time.struct_time) -> aware UTC datetime."""
        for key in ("published_parsed", "updated_parsed"):
            parsed = entry.get(key)
            if parsed:
                try:
                    return datetime(*parsed[:6], tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    continue
        return datetime.now(timezone.utc)
