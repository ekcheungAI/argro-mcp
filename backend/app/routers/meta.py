"""Routers for /meta/* (docs/03-http-api-spec.md §2.5-2.6)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import optional_api_key
from app.models.article import Article
from app.models.article_translation import ArticleTranslation
from app.models.source import Source
from app.models.topic import Topic
from app.schemas.meta import SourceMeta, SourcesResponse, TopicMeta, TopicsResponse

router = APIRouter(prefix="/meta", tags=["meta"], dependencies=[Depends(optional_api_key)])


@router.get("/sources", response_model=SourcesResponse)
def get_meta_sources(db: Session = Depends(get_db)) -> SourcesResponse:
    """GET /meta/sources — active sources (docs/03 §2.5)."""
    rows = db.execute(
        select(Source).where(Source.is_active.is_(True)).order_by(Source.name)
    ).scalars().all()
    return SourcesResponse(
        sources=[
            SourceMeta(
                id=str(src.id),
                name=src.name,
                type=src.type,
                lang=src.lang,
                homepage_url=src.homepage_url,
                feed_url=src.feed_url,
                priority_weight=src.priority_weight,
                is_active=src.is_active,
            )
            for src in rows
        ]
    )


@router.get("/topics", response_model=TopicsResponse)
def get_meta_topics(db: Session = Depends(get_db)) -> TopicsResponse:
    """GET /meta/topics — full topic taxonomy (docs/03 §2.6)."""
    rows = db.execute(select(Topic).order_by(Topic.id)).scalars().all()
    return TopicsResponse(
        topics=[
            TopicMeta(key=t.key, name=t.name, description=t.description) for t in rows
        ]
    )


@router.get("/health")
def get_meta_health(db: Session = Depends(get_db)):
    """GET /meta/health — pipeline 健康監察(sources 抓取狀態、items 統計、蒸餾進度)。"""
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    total = db.execute(select(func.count()).select_from(Article)).scalar() or 0
    today_count = (
        db.execute(select(func.count()).select_from(Article).where(Article.fetched_at >= today)).scalar() or 0
    )
    week_count = (
        db.execute(select(func.count()).select_from(Article).where(Article.fetched_at >= week_ago)).scalar() or 0
    )
    unclassified = (
        db.execute(
            select(func.count()).select_from(Article).where(func.coalesce(func.cardinality(Article.topics_cached), 0) == 0)
        ).scalar()
        or 0
    )
    untranslated = (
        db.execute(
            select(func.count())
            .select_from(Article)
            .where(Article.original_lang != "zh-TW")
            .where(
                ~Article.id.in_(
                    select(ArticleTranslation.article_id).where(
                        ArticleTranslation.lang == "zh-TW"
                    )
                )
            )
        ).scalar()
        or 0
    )
    last_fetch = db.execute(select(func.max(Article.fetched_at))).scalar()

    src_rows = db.execute(select(Source).order_by(Source.name)).scalars().all()
    sources_out = []
    for src in src_rows:
        src_today = (
            db.execute(
                select(func.count())
                .select_from(Article)
                .where(Article.source_id == src.id)
                .where(Article.fetched_at >= today)
            ).scalar()
            or 0
        )
        src_last = db.execute(
            select(func.max(Article.fetched_at)).where(Article.source_id == src.id)
        ).scalar()
        if not src.is_active:
            status = "paused"
        elif src_last is None:
            status = "down"
        elif src_today > 0 or (now - src_last) < timedelta(hours=26):
            status = "ok"
        elif (now - src_last) < timedelta(days=3):
            status = "warn"
        else:
            status = "down"
        sources_out.append(
            {
                "id": str(src.id),
                "name": src.name,
                "type": src.type,
                "lang": src.lang,
                "is_active": src.is_active,
                "status": status,
                "last_fetch": src_last.isoformat() if src_last else None,
                "items_today": src_today,
            }
        )

    return {
        "status": "ok",
        "now": now.isoformat(),
        "llm": {
            "configured": bool(settings.moonshot_api_key),
            "base_url": settings.moonshot_base_url,
            "model": settings.translation_model,
        },
        "articles": {
            "total": total,
            "today": today_count,
            "week": week_count,
            "unclassified": unclassified,
            "untranslated_zh_tw": untranslated,
        },
        "last_fetch": last_fetch.isoformat() if last_fetch else None,
        "sources": sources_out,
    }
