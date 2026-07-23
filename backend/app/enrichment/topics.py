"""Topic classification enrichment (docs/05 §4).

Classifies articles into 0-3 predefined topic keys with a confidence score:
- With an LLM available: prompt with the topics table (key + description) and
  parse the JSON answer.
- Without an LLM: keyword heuristics (KEYWORD_TOPIC_MAP) so articles still get
  basic labels.

Results are upserted into ``article_topics`` and ``articles.topics_cached`` is
maintained with the keys whose confidence >= TOPICS_CACHED_THRESHOLD.
"""
from __future__ import annotations

import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.enrichment.llm import LLMProvider, get_client
from app.models import Article, ArticleTopic, Topic

logger = logging.getLogger(__name__)

MAX_TOPICS_PER_ARTICLE = 3
TOPICS_CACHED_THRESHOLD = 0.5
FALLBACK_CONFIDENCE = 0.55

# Keyword heuristics (lowercase substring -> topic key). First match wins per
# topic; confidence is fixed at FALLBACK_CONFIDENCE so it just clears the
# topics_cached threshold.
KEYWORD_TOPIC_MAP: list[tuple[str, tuple[str, ...]]] = [
    ("model_release", ("gpt-", "llm", "model release", "new model", "checkpoint", "weights", "multimodal model")),
    ("product_update", ("release", "launch", "introducing", "now available", "update", "feature", "api", "app")),
    ("industry_event", ("funding", "raises", "acquisition", "acquires", "conference", "keynote", "partnership", "ipo")),
    ("policy", ("policy", "regulation", "regulator", "ban", "law", "act ", "congress", "eu ai", "executive order", "antitrust", "safety standard")),
    ("research_paper", ("paper", "arxiv", "preprint", "benchmark", "study finds", "we propose", "dataset")),
    ("opinion_tutorial", ("opinion", "how to", "tutorial", "guide", "explainer", "analysis:", "hands-on")),
]

_PROMPT_TEMPLATE = """\
You are classifying an AI-industry news article into predefined topics.

Available topics:
{topic_lines}

Article title: {title}
Article summary: {summary}

Pick between 0 and {max_topics} topics that best describe the article.
Return ONLY a JSON array (no markdown fences, no commentary), e.g.:
[{{"key": "model_release", "confidence": 0.9}}, {{"key": "product_update", "confidence": 0.6}}]
Use only keys from the list above; confidence is a float in [0, 1]. Return [] if nothing fits.
"""


def classify_article(
    session: Session,
    article: Article,
    topics: list[Topic],
    client: LLMProvider | None = None,
) -> list[tuple[str, float]]:
    """Return [(topic_key, confidence)] for an article (LLM or heuristic)."""
    client = client or get_client()
    if client.available():
        results = _classify_with_llm(article, topics, client)
        if results is not None:
            return results
        logger.info("LLM classification failed for article %s; falling back to keywords", article.id)
    return _classify_with_keywords(article)


def _classify_with_llm(
    article: Article, topics: list[Topic], client: LLMProvider
) -> list[tuple[str, float]] | None:
    topic_lines = "\n".join(f"- {t.key}: {t.description or t.name}" for t in topics)
    prompt = _PROMPT_TEMPLATE.format(
        topic_lines=topic_lines,
        title=article.title,
        summary=article.summary or "",
        max_topics=MAX_TOPICS_PER_ARTICLE,
    )
    parsed = client.chat_json(prompt)
    if not isinstance(parsed, list):
        return None
    valid_keys = {t.key for t in topics}
    results: list[tuple[str, float]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        try:
            confidence = float(item.get("confidence", 0))
        except (TypeError, ValueError):
            continue
        if key in valid_keys and 0 <= confidence <= 1:
            results.append((key, confidence))
    results.sort(key=lambda kv: kv[1], reverse=True)
    return results[:MAX_TOPICS_PER_ARTICLE]


def _classify_with_keywords(article: Article) -> list[tuple[str, float]]:
    """Simple keyword -> topic mapping; guarantees basic labels without an LLM."""
    text = f"{article.title} {article.summary or ''}".lower()
    results: list[tuple[str, float]] = []
    for topic_key, keywords in KEYWORD_TOPIC_MAP:
        if any(kw in text for kw in keywords):
            results.append((topic_key, FALLBACK_CONFIDENCE))
        if len(results) >= MAX_TOPICS_PER_ARTICLE:
            break
    return results


def apply_classification(
    session: Session, article: Article, topics: list[Topic], results: list[tuple[str, float]]
) -> None:
    """Upsert article_topics rows and refresh articles.topics_cached."""
    key_to_id = {t.key: t.id for t in topics}
    # Replace previous classification for this article (idempotent re-runs).
    session.execute(delete(ArticleTopic).where(ArticleTopic.article_id == article.id))
    cached: list[str] = []
    for key, confidence in results:
        topic_id = key_to_id.get(key)
        if topic_id is None:
            continue
        session.add(ArticleTopic(article_id=article.id, topic_id=topic_id, confidence=confidence))
        if confidence >= TOPICS_CACHED_THRESHOLD:
            cached.append(key)
    article.topics_cached = cached


def classify_pending(session: Session, limit: int = 100, client: LLMProvider | None = None) -> int:
    """Classify recent articles that have no article_topics rows yet."""
    client = client or get_client()
    topics = session.execute(select(Topic).order_by(Topic.id)).scalars().all()
    if not topics:
        logger.warning("No topics in DB; run `python -m app.seed` first")
        return 0

    already = select(ArticleTopic.article_id)
    articles = (
        session.execute(
            select(Article)
            .where(Article.status == "active", Article.id.notin_(already))
            .order_by(Article.fetched_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )

    classified = 0
    for article in articles:
        results = classify_article(session, article, topics, client)
        apply_classification(session, article, topics, results)
        classified += 1

    if classified:
        session.commit()
    mode = "llm" if client.available() else "keyword-fallback"
    logger.info("Topic classification (%s): %d articles classified", mode, classified)
    return classified
