"""Translation enrichment (docs/05 §3.2).

For each article and each configured target language (that differs from the
article's original language), translate title+summary via the LLM and upsert
into ``article_translations`` with ``translation_model`` recorded.

Graceful: without an LLM API key the whole step logs and no-ops.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.enrichment.llm import LLMProvider, get_client
from app.models import Article, ArticleTranslation

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """\
Translate the following news article title and summary into {target_lang}.

Return ONLY a JSON object with keys "title" and "summary" (no markdown fences, no commentary).
If a field is empty in the input, return an empty string for it.

Title: {title}

Summary: {summary}
"""


def translate_article(
    article: Article,
    target_lang: str,
    client: LLMProvider | None = None,
) -> ArticleTranslation | None:
    """Translate one article into one language; returns an (unsaved) translation or None."""
    client = client or get_client()
    if not client.available():
        return None
    prompt = _PROMPT_TEMPLATE.format(
        target_lang=target_lang,
        title=article.title,
        summary=article.summary or "",
    )
    result = client.chat_json(prompt, model=settings.translation_model)
    if not isinstance(result, dict) or not result.get("title"):
        logger.warning("Translation failed for article %s -> %s", article.id, target_lang)
        return None
    return ArticleTranslation(
        article_id=article.id,
        lang=target_lang,
        title=str(result["title"]).strip(),
        summary=str(result.get("summary") or "").strip() or None,
        translation_model=settings.translation_model,
    )


def translate_pending(session: Session, limit: int = 50, client: LLMProvider | None = None) -> int:
    """Translate recent articles into missing target languages. Returns translations written."""
    client = client or get_client()
    if not client.available():
        logger.info("Translation skipped: LLM provider not available (no API key)")
        return 0

    target_langs = settings.target_langs_list
    if not target_langs:
        return 0

    articles = (
        session.execute(
            select(Article)
            .where(Article.status == "active", Article.original_lang.notin_(["unknown", ""]))
            .order_by(Article.fetched_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )

    written = 0
    for article in articles:
        existing = {
            t.lang
            for t in session.execute(
                select(ArticleTranslation).where(ArticleTranslation.article_id == article.id)
            )
            .scalars()
            .all()
        }
        for lang in target_langs:
            # Skip when the article is already in the target language or translated.
            if lang == article.original_lang or lang in existing:
                continue
            translation = translate_article(article, lang, client)
            if translation is None:
                continue
            # Upsert: replace any existing row for (article_id, lang).
            current = session.execute(
                select(ArticleTranslation).where(
                    ArticleTranslation.article_id == article.id,
                    ArticleTranslation.lang == lang,
                )
            ).scalar_one_or_none()
            if current is not None:
                current.title = translation.title
                current.summary = translation.summary
                current.translation_model = translation.translation_model
            else:
                session.add(translation)
            written += 1

    if written:
        session.commit()
    logger.info("Translation: %d translations written across %d articles", written, len(articles))
    return written
