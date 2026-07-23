"""Embedding enrichment (docs/05 §5).

Generates an embedding per article from cleaned ``title + summary (+ content
prefix)`` and upserts into ``article_embeddings`` with the model name
recorded. Provider-agnostic via the LLMProvider.embed interface; the default
Moonshot client calls the OpenAI-compatible /embeddings endpoint and returns
None when unsupported -- in which case this step no-ops.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.enrichment.llm import LLMProvider, get_client
from app.models import Article, ArticleEmbedding

logger = logging.getLogger(__name__)

# Content is unbounded; cap the text we send to the embedding model.
MAX_TEXT_CHARS = 4000


def article_text(article: Article) -> str:
    """Cleaned text used for embedding: title + summary + content prefix."""
    parts = [article.title, article.summary or "", (article.content or "")[:MAX_TEXT_CHARS]]
    return "\n".join(part for part in parts if part).strip()


def embed_articles(
    session: Session, articles: list[Article], client: LLMProvider | None = None
) -> int:
    """Embed a batch of articles; returns the number of rows written."""
    client = client or get_client()
    if not client.available() or not articles:
        return 0
    texts = [article_text(a) for a in articles]
    vectors = client.embed(texts, model=settings.embedding_model)
    if not vectors or len(vectors) != len(articles):
        logger.info("Embedding provider returned no vectors; embedding step skipped")
        return 0

    written = 0
    for article, vector in zip(articles, vectors):
        existing = session.execute(
            select(ArticleEmbedding).where(ArticleEmbedding.article_id == article.id)
        ).scalar_one_or_none()
        if existing is not None:
            existing.embedding = vector
            existing.model = settings.embedding_model
        else:
            session.add(
                ArticleEmbedding(
                    article_id=article.id,
                    embedding=vector,
                    model=settings.embedding_model,
                )
            )
        written += 1
    return written


def embed_pending(session: Session, limit: int = 50, client: LLMProvider | None = None) -> int:
    """Embed recent articles that have no embedding yet. Returns rows written."""
    client = client or get_client()
    if not client.available():
        logger.info("Embedding skipped: LLM provider not available (no API key)")
        return 0

    already = select(ArticleEmbedding.article_id)
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
    written = embed_articles(session, articles, client)
    if written:
        session.commit()
    logger.info("Embedding: %d/%d articles embedded", written, len(articles))
    return written
