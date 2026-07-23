"""Routers for /news/* (docs/03-http-api-spec.md §2.1-2.3).

Route registration order matters: the literal paths ``/stream`` and ``/hot``
are declared before ``/{id}`` so they are matched first.
"""
import uuid
from datetime import datetime, time, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import (
    SORT_HOT_DESC,
    SORT_TIME_DESC,
    apply_cursor,
    encode_cursor,
    optional_api_key,
    order_by_sort,
    parse_date_param,
    parse_datetime_param,
    resolve_lang,
)
from app.models.article import Article
from app.models.article_topic import ArticleTopic
from app.models.article_translation import ArticleTranslation
from app.models.source import Source
from app.models.topic import Topic
from app.schemas.news import (
    ArticleDetail,
    ClusterRelated,
    NewsStreamItem,
    NewsStreamResponse,
    SourceBrief,
    SourceDetail,
    TopicBrief,
)

router = APIRouter(prefix="/news", tags=["news"], dependencies=[Depends(optional_api_key)])


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _parse_source_ids(value: str) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    for part in _split_csv(value):
        try:
            ids.append(uuid.UUID(part))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid 'source' id: {part}") from exc
    return ids


def _prefetch_translations(
    db: Session, article_ids: list[uuid.UUID], lang: Optional[str]
) -> dict[uuid.UUID, ArticleTranslation]:
    """Fetch translations for the requested language in one query (no N+1)."""
    if not lang or not article_ids:
        return {}
    rows = db.execute(
        select(ArticleTranslation).where(
            ArticleTranslation.article_id.in_(article_ids),
            ArticleTranslation.lang == lang,
        )
    ).scalars().all()
    return {row.article_id: row for row in rows}


def _build_stream_items(
    db: Session,
    rows: list[tuple[Article, Source]],
    lang: Optional[str],
) -> list[NewsStreamItem]:
    translations_map = _prefetch_translations(db, [a.id for a, _ in rows], lang)
    items: list[NewsStreamItem] = []
    for article, source in rows:
        resolved = resolve_lang(article, translations_map, lang)
        items.append(
            NewsStreamItem(
                id=str(article.id),
                title=resolved["title"],
                summary=resolved["summary"],
                url=article.url,
                lang=resolved["lang"],
                original_lang=article.original_lang,
                published_at=article.published_at,
                source=SourceBrief(id=str(source.id), name=source.name),
                topics=list(article.topics_cached or []),
                hot_score=article.hot_score,
                cluster_id=str(article.cluster_id) if article.cluster_id else None,
            )
        )
    return items


@router.get("/stream", response_model=NewsStreamResponse)
def get_news_stream(
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = Query(default=None),
    lang: Optional[str] = Query(default=None),
    topic: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    sort: str = Query(default=SORT_TIME_DESC, pattern="^(time_desc|hot_desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> NewsStreamResponse:
    """GET /news/stream — paginated article list (docs/03 §2.1)."""
    query = (
        select(Article, Source)
        .join(Source, Article.source_id == Source.id)
        .where(Article.status == "active")
    )

    # --- filters -----------------------------------------------------------
    if from_:
        query = query.where(
            Article.published_at >= parse_datetime_param(from_, param="from")
        )
    if to:
        # Date-only `to` includes the whole day (end-of-day UTC); omitted `to`
        # naturally means "up to now" because we only filter on published_at.
        query = query.where(
            Article.published_at <= parse_datetime_param(to, param="to", end_of_day=True)
        )
    if topic:
        # Fast path: topics_cached is a text[] with a GIN index -> use `&&` (overlap).
        # (Equivalent join via article_topics/topics is possible but slower.)
        query = query.where(Article.topics_cached.overlap(_split_csv(topic)))
    if source:
        query = query.where(Article.source_id.in_(_parse_source_ids(source)))
    if q:
        pattern = f"%{q}%"
        # NOTE: semantic (pgvector) search interface point — when embeddings
        # are available, rank by article_embeddings.embedding <=> embed(q)
        # instead of / in addition to this ILIKE fallback.
        query = query.where(
            or_(Article.title.ilike(pattern), Article.summary.ilike(pattern))
        )

    # --- keyset pagination --------------------------------------------------
    if cursor:
        query = apply_cursor(query, cursor, sort)
    query = order_by_sort(query, sort)
    query = query.limit(limit + 1)  # one extra row to detect a next page

    rows = db.execute(query).all()
    page_rows = list(rows[:limit])
    items = _build_stream_items(db, page_rows, lang)

    next_cursor: Optional[str] = None
    if len(rows) > limit and page_rows:
        last_article, _ = page_rows[-1]
        sort_value = last_article.hot_score if sort == SORT_HOT_DESC else last_article.published_at
        next_cursor = encode_cursor(sort_value, last_article.id)

    return NewsStreamResponse(items=items, next_cursor=next_cursor)


@router.get("/hot", response_model=NewsStreamResponse)
def get_news_hot(
    date: Optional[str] = Query(default=None),
    lang: Optional[str] = Query(default=None),
    topic: Optional[str] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> NewsStreamResponse:
    """GET /news/hot — hottest articles of a day (docs/03 §2.2)."""
    day = parse_date_param(date, param="date") if date else datetime.now(timezone.utc).date()
    day_start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    query = (
        select(Article, Source)
        .join(Source, Article.source_id == Source.id)
        .where(
            Article.status == "active",
            Article.published_at >= day_start,
            Article.published_at < day_end,
        )
    )
    if topic:
        query = query.where(Article.topics_cached.overlap(_split_csv(topic)))
    query = query.order_by(Article.hot_score.desc(), Article.id.desc()).limit(limit)

    rows = list(db.execute(query).all())
    items = _build_stream_items(db, rows, lang)
    # No cursor for the hot list (spec allows next_cursor to be null).
    return NewsStreamResponse(items=items, next_cursor=None)


@router.get("/{id}", response_model=ArticleDetail)
def get_news_article(
    id: str,
    lang: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> ArticleDetail:
    """GET /news/{id} — single article detail (docs/03 §2.3)."""
    try:
        article_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Article not found")

    row = db.execute(
        select(Article, Source)
        .join(Source, Article.source_id == Source.id)
        .where(Article.id == article_uuid, Article.status == "active")
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Article not found")
    article, source = row

    translations_map = _prefetch_translations(db, [article.id], lang)
    resolved = resolve_lang(article, translations_map, lang)

    topic_rows = db.execute(
        select(Topic.key, Topic.name, ArticleTopic.confidence)
        .join(ArticleTopic, ArticleTopic.topic_id == Topic.id)
        .where(ArticleTopic.article_id == article.id)
    ).all()
    topics = [
        TopicBrief(key=key, name=name, confidence=confidence)
        for key, name, confidence in topic_rows
    ]

    cluster_related: list[ClusterRelated] = []
    if article.cluster_id:
        related_rows = db.execute(
            select(Article, Source)
            .join(Source, Article.source_id == Source.id)
            .where(
                Article.cluster_id == article.cluster_id,
                Article.id != article.id,
                Article.status == "active",
            )
            .order_by(Article.hot_score.desc())
            .limit(5)
        ).all()
        cluster_related = [
            ClusterRelated(
                id=str(rel.id),
                title=rel.title,
                url=rel.url,
                source=SourceBrief(id=str(rel_source.id), name=rel_source.name),
            )
            for rel, rel_source in related_rows
        ]

    return ArticleDetail(
        id=str(article.id),
        title=resolved["title"],
        summary=resolved["summary"],
        content=resolved["content"],
        url=article.url,
        lang=resolved["lang"],
        original_lang=article.original_lang,
        published_at=article.published_at,
        source=SourceDetail(
            id=str(source.id), name=source.name, homepage_url=source.homepage_url
        ),
        topics=topics,
        hot_score=article.hot_score,
        cluster_id=str(article.cluster_id) if article.cluster_id else None,
        cluster_related=cluster_related,
        metadata=dict(article.meta or {}),
    )
