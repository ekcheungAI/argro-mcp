"""Daily insight generation (docs/05 §7).

``generate_daily_insight`` takes the day's top-N articles by hot_score and
produces a ``daily_insights`` row (unique on (type, date, lang)):

- With an LLM available: title/summary/sections are generated as JSON
  (sections = [{section_title, content, articles: [article_id...]}]).
- Without an LLM: a deterministic fallback -- title "YYYY-MM-DD AI
  Highlights", summary = top-3 article titles joined, sections grouped by the
  articles' cached topics -- so the pipeline still works keyless.

``generated_from`` records the model name (or "fallback") and the referenced
article ids.
"""
from __future__ import annotations

import logging
from datetime import date as date_type
from datetime import datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.enrichment.llm import LLMProvider, get_client
from app.models import Article, DailyInsight

logger = logging.getLogger(__name__)

TOP_N_ARTICLES = 10
FALLBACK_SUMMARY_TITLES = 3
INSIGHT_TYPE = "daily"

_PROMPT_TEMPLATE = """\
You are writing the daily AI news digest for {day} (language: {lang}).

Here are today's top {n} AI news articles (hottest first):
{article_lines}

Write a concise daily digest in {lang}. Return ONLY a JSON object (no markdown fences):
{{
  "title": "<short digest title>",
  "summary": "<2-3 sentence overview of the day>",
  "sections": [
    {{
      "section_title": "<theme name>",
      "content": "<short paragraph about this theme>",
      "articles": ["A1", "A4", ...]
    }}
  ]
}}
Group the articles into 2-4 thematic sections; every section's "articles" must use ONLY the A-labels from the list above (e.g. "A3") — never titles, URLs, or UUIDs.
"""


def _top_articles(session: Session, day: date_type, limit: int = TOP_N_ARTICLES) -> list[Article]:
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = datetime.combine(day, time.max, tzinfo=timezone.utc)
    return (
        session.execute(
            select(Article)
            .where(Article.status == "active", Article.published_at.between(start, end))
            .order_by(Article.hot_score.desc(), Article.published_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )


def _llm_insight(articles: list[Article], day: date_type, lang: str, client: LLMProvider) -> dict | None:
    # LLM 用短 alias(A1..An)引用文章 — 完整 UUID 喺 prompt 入面 LLM 成日抄錯,
    # 搞到 sanitize 後 articles 全部變空。alias 映射返真 id 先可靠。
    labels = {f"A{i + 1}": str(a.id) for i, a in enumerate(articles)}
    article_lines = "\n".join(
        f'- {label} | topics={",".join(a.topics_cached or [])} | {a.title} -- {a.summary or ""}'
        for label, a in zip(labels, articles)
    )
    prompt = _PROMPT_TEMPLATE.format(day=day.isoformat(), lang=lang, n=len(articles), article_lines=article_lines)
    parsed = client.chat_json(prompt, model=settings.translation_model)
    if not isinstance(parsed, dict) or not parsed.get("title") or not isinstance(parsed.get("sections"), list):
        logger.warning("LLM insight generation returned unusable payload for %s (%s)", day, lang)
        return None
    # Sanitize section article ids:A-label → 真 id;兼容 LLM 直接回 UUID 嘅情況。
    known_ids = {str(a.id) for a in articles}
    sections = []
    for section in parsed["sections"]:
        if not isinstance(section, dict):
            continue
        mapped: list[str] = []
        for raw in section.get("articles", []):
            key = str(raw).strip().upper()
            candidate = labels.get(key) or (str(raw) if str(raw) in known_ids else None)
            if candidate and candidate not in mapped:
                mapped.append(candidate)
        sections.append(
            {
                "section_title": str(section.get("section_title", "")).strip() or "Highlights",
                "content": str(section.get("content", "")).strip(),
                "articles": mapped,
            }
        )
    # Safety net:如果 LLM 嘅引用全部無效(所有 section 都空),
    # 按 hot 順序 round-robin 分配,保證 daily 有真文章連結。
    if sections and not any(s["articles"] for s in sections):
        logger.warning("LLM insight %s (%s): all article refs invalid — round-robin fallback", day, lang)
        ids = [str(a.id) for a in articles]
        for idx, article_id in enumerate(ids):
            sections[idx % len(sections)]["articles"].append(article_id)
    return {
        "title": str(parsed["title"]).strip(),
        "summary": str(parsed.get("summary", "")).strip(),
        "sections": sections,
    }


def _fallback_insight(articles: list[Article], day: date_type) -> dict:
    """Deterministic non-LLM digest: top titles + topic-grouped sections."""
    title = f"{day.isoformat()} AI Highlights"
    summary = " | ".join(a.title for a in articles[:FALLBACK_SUMMARY_TITLES])

    by_topic: dict[str, list[Article]] = {}
    for article in articles:
        key = (article.topics_cached or ["uncategorized"])[0]
        by_topic.setdefault(key, []).append(article)
    sections = [
        {
            "section_title": topic.replace("_", " ").title(),
            "content": " | ".join(a.title for a in group),
            "articles": [str(a.id) for a in group],
        }
        for topic, group in by_topic.items()
    ]
    return {"title": title, "summary": summary, "sections": sections}


def generate_daily_insight(
    session: Session,
    day: date_type,
    lang: str,
    client: LLMProvider | None = None,
) -> DailyInsight | None:
    """Generate (or regenerate) the daily insight for ``day`` + ``lang``.

    Upserts on the unique (type, date, lang) key. Returns the row, or None
    when there are no articles for the day.
    """
    client = client or get_client()
    articles = _top_articles(session, day)
    if not articles:
        logger.info("No articles on %s; skipping insight generation (%s)", day, lang)
        return None

    used_llm = False
    if client.available():
        payload = _llm_insight(articles, day, lang, client)
        used_llm = payload is not None
    else:
        payload = None
        logger.info("LLM not available; using fallback insight generator for %s (%s)", day, lang)
    if payload is None:
        payload = _fallback_insight(articles, day)

    generated_from = {
        "model": settings.translation_model if used_llm else "fallback",
        "article_ids": [str(a.id) for a in articles],
        "top_n": len(articles),
    }

    insight = session.execute(
        select(DailyInsight).where(
            DailyInsight.type == INSIGHT_TYPE,
            DailyInsight.date == day,
            DailyInsight.lang == lang,
        )
    ).scalar_one_or_none()
    created = insight is None
    if created:
        insight = DailyInsight(type=INSIGHT_TYPE, date=day, lang=lang)
        session.add(insight)
    insight.title = payload["title"]
    insight.summary = payload["summary"]
    insight.sections = payload["sections"]
    insight.generated_from = generated_from

    session.commit()
    logger.info(
        "Daily insight for %s (%s) %s: %d articles, generator=%s",
        day,
        lang,
        "created" if created else "updated",
        len(articles),
        generated_from["model"],
    )
    return insight
