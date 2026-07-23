"""Hot score calculation (docs/05 §6).

    score = source.priority_weight * recency_decay * (1 + info_value_bonus)

- recency_decay: exponential decay from published_at with ~12h half-life.
- info_value_bonus: 0 by default. An optional LLM-based "information value"
  scorer is provided behind the HOT_SCORE_LLM_ENABLED env flag (interface
  only; off unless explicitly enabled and an API key is configured).
"""
from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enrichment.llm import LLMProvider, get_client
from app.models import Article, Source

logger = logging.getLogger(__name__)

# Half-life in hours for the exponential recency decay.
RECENCY_HALF_LIFE_HOURS = 12.0
RESCORE_WINDOW_HOURS = 48


def recency_decay(published_at: datetime, now: datetime | None = None) -> float:
    """Exponential decay in (0, 1]: 0.5 ** (age_hours / half_life)."""
    now = now or datetime.now(timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    age_hours = max(0.0, (now - published_at).total_seconds() / 3600.0)
    return math.pow(0.5, age_hours / RECENCY_HALF_LIFE_HOURS)


def llm_info_value_bonus(article: Article, client: LLMProvider | None = None) -> float:
    """Optional LLM-based information-value bonus in [0, 1].

    Disabled unless HOT_SCORE_LLM_ENABLED is truthy; returns 0 when disabled,
    when no API key is configured, or when the LLM answer is unparseable.
    """
    if os.getenv("HOT_SCORE_LLM_ENABLED", "").lower() not in ("1", "true", "yes"):
        return 0.0
    client = client or get_client()
    if not client.available():
        return 0.0
    prompt = (
        "Rate the information value of this AI news article on a scale of 0 to 1 "
        "(0 = noise/clickbait, 1 = major development). Reply with ONLY the number.\n\n"
        f"Title: {article.title}\nSummary: {article.summary or ''}"
    )
    text = client.chat(prompt)
    if text is None:
        return 0.0
    try:
        value = float(text.strip())
    except ValueError:
        logger.warning("Unparseable info-value score %r for article %s", text[:50], article.id)
        return 0.0
    return max(0.0, min(1.0, value))


def compute_score(article: Article, source: Source, info_value_bonus: float = 0.0) -> float:
    """hot_score = source.priority_weight * recency_decay * (1 + info_value_bonus)."""
    return source.priority_weight * recency_decay(article.published_at) * (1.0 + info_value_bonus)


def rescore_recent(
    session: Session,
    hours: int = RESCORE_WINDOW_HOURS,
    client: LLMProvider | None = None,
) -> int:
    """Recompute hot_score for articles published within the last ``hours`` hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = (
        session.execute(
            select(Article, Source)
            .join(Source, Article.source_id == Source.id)
            .where(Article.status == "active", Article.published_at >= cutoff)
        )
        .all()
    )
    rescored = 0
    for article, source in rows:
        article.hot_score = compute_score(article, source, llm_info_value_bonus(article, client))
        rescored += 1
    if rescored:
        session.commit()
    logger.info("Hot score: rescored %d articles from the last %dh", rescored, hours)
    return rescored
