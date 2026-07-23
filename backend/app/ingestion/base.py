"""Base types for ingestion: RawArticle, Fetcher protocol, normalization helpers.

See docs/05-source-ingestion-spec.md §2 for the RawArticle shape.
"""
from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# Max lengths to keep junk out of the DB.
MAX_TITLE_LEN = 1024
MAX_SUMMARY_LEN = 8192
MAX_CONTENT_LEN = 200_000

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass
class RawArticle:
    """Normalized in-memory article, per docs/05 §2.3.

    ``published_at`` accepts an ISO string or a datetime; ``to_insert_kwargs``
    normalizes it to a timezone-aware UTC datetime.
    """

    source_id: Any  # uuid.UUID of the sources row
    url: str
    title: str
    external_id: str | None = None
    summary: str | None = None
    content: str | None = None
    published_at: str | datetime | None = None
    metadata: dict | None = field(default=None)

    def to_insert_kwargs(self) -> dict:
        """Return normalized kwargs suitable for constructing an Article row."""
        return {
            "source_id": self.source_id,
            "external_id": (self.external_id or "").strip() or None,
            "url": self.url.strip(),
            "title": _clip(_clean_text(self.title), MAX_TITLE_LEN),
            "summary": _clip(_clean_text(self.summary), MAX_SUMMARY_LEN) if self.summary else None,
            "content": _clip(self.content.strip(), MAX_CONTENT_LEN) if self.content else None,
            "published_at": normalize_published_at(self.published_at),
            "meta": self.metadata or {},
        }


@runtime_checkable
class Fetcher(Protocol):
    """Anything that can fetch raw articles for a source."""

    def fetch(self, source) -> list[RawArticle]:
        """Fetch and normalize articles for ``source``.

        Implementations must be robust: on any fetch/parse failure they should
        log and return an empty list instead of raising.
        """
        ...


def strip_html(value: str | None) -> str | None:
    """Remove HTML tags, unescape entities and collapse whitespace."""
    if not value:
        return None
    text = _TAG_RE.sub(" ", value)
    text = html.unescape(text)
    text = _WS_RE.sub(" ", text).strip()
    return text or None


def _clean_text(value: str | None) -> str:
    """Collapse whitespace; keep as plain text."""
    if not value:
        return ""
    return _WS_RE.sub(" ", html.unescape(value)).strip()


def _clip(value: str, max_len: int) -> str:
    return value[:max_len]


def normalize_published_at(value: str | datetime | None) -> datetime:
    """Normalize an ISO string / datetime to an aware UTC datetime.

    Falls back to ``now()`` when missing or unparseable (published_at is
    NOT NULL in the schema).
    """
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        raw = value.strip()
        # Tolerate a trailing "Z" (Python <3.11 fromisoformat can't parse it).
        if raw.endswith(("Z", "z")):
            raw = raw[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            logger.warning("Unparseable published_at %r; using now()", value)
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
