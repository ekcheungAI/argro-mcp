"""Routers for /meta/* (docs/03-http-api-spec.md §2.5-2.6)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import optional_api_key
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
