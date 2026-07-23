"""Language detection enrichment (docs/05 §3.1).

Detects ``original_lang`` from title+summary using langdetect for articles
whose language is still 'unknown' / empty. No LLM required.
"""
from __future__ import annotations

import logging

from langdetect import DetectorFactory, LangDetectException, detect
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Article

logger = logging.getLogger(__name__)

# langdetect is non-deterministic for short texts; seed for reproducibility.
DetectorFactory.seed = 0

UNKNOWN_VALUES = ("unknown", "", None)


def detect_lang(text: str) -> str | None:
    """Detect a BCP-47-ish language code, or None if undetectable."""
    if not text or not text.strip():
        return None
    try:
        return detect(text)
    except LangDetectException:
        return None


def detect_pending(session: Session, limit: int = 200) -> int:
    """Fill original_lang for articles where it is unknown. Returns count updated."""
    articles = (
        session.execute(
            select(Article)
            .where(or_(Article.original_lang.is_(None), Article.original_lang.in_(["unknown", ""])))
            .order_by(Article.fetched_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    updated = 0
    for article in articles:
        lang = detect_lang(f"{article.title}\n{article.summary or ''}")
        if lang:
            article.original_lang = lang
            updated += 1
        else:
            # Mark as the source's language is unknown; keep 'unknown' so a
            # future run can retry (e.g. after content is backfilled).
            logger.debug("Could not detect language for article %s", article.id)
    if updated:
        session.commit()
    logger.info("Language detection: %d/%d articles updated", updated, len(articles))
    return updated
