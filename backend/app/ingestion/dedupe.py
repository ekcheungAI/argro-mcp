"""Deduplication + upsert logic (docs/05 §2.4-2.5).

Strategy:
1. If ``external_id`` is present, look up (source_id, external_id).
2. Fall back to (source_id, url).
3. Existing row -> refresh fetched_at, backfill summary/content/external_id
   only where the stored value is NULL (don't clobber enrichment output).
4. New row -> insert with status='active', hot_score=0.

The caller owns the transaction (commit/rollback).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.base import RawArticle
from app.models import Article

logger = logging.getLogger(__name__)


def upsert_article(session: Session, source, raw: RawArticle) -> tuple[Article, bool]:
    """Insert or update an article from a RawArticle.

    Returns ``(article, created)`` where ``created`` is True for a new row.
    """
    kwargs = raw.to_insert_kwargs()
    now = datetime.now(timezone.utc)

    article = _find_existing(session, source.id, kwargs["external_id"], kwargs["url"])
    if article is not None:
        _refresh_existing(article, kwargs, now)
        return article, False

    article = Article(
        original_lang=(source.lang or "unknown"),
        fetched_at=now,
        status="active",
        hot_score=0.0,
        **kwargs,
    )
    session.add(article)
    session.flush()  # assign id / surface constraint errors inside caller's txn
    return article, True


def _find_existing(session: Session, source_id, external_id: str | None, url: str) -> Article | None:
    """Prefer unique (source_id, external_id); fallback on (source_id, url)."""
    if external_id:
        article = session.execute(
            select(Article).where(
                Article.source_id == source_id,
                Article.external_id == external_id,
            )
        ).scalar_one_or_none()
        if article is not None:
            return article
    return session.execute(
        select(Article).where(
            Article.source_id == source_id,
            Article.url == url,
        )
    ).scalar_one_or_none()


def _refresh_existing(article: Article, kwargs: dict, now: datetime) -> None:
    """Update fetched_at and backfill fields that are still NULL."""
    article.fetched_at = now
    if article.external_id is None and kwargs["external_id"]:
        article.external_id = kwargs["external_id"]
    if article.summary is None and kwargs["summary"]:
        article.summary = kwargs["summary"]
    if article.content is None and kwargs["content"]:
        article.content = kwargs["content"]
    # Merge feed metadata keys we don't have yet (never overwrite).
    if kwargs.get("meta"):
        merged = {**(kwargs["meta"]), **(article.meta or {})}
        if merged != article.meta:
            article.meta = merged
