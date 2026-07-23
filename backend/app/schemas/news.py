"""Response schemas for /news/* endpoints (docs/03-http-api-spec.md §2.1-2.3)."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class SourceBrief(BaseModel):
    id: str
    name: str


class SourceDetail(BaseModel):
    id: str
    name: str
    homepage_url: str


class NewsStreamItem(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    url: str
    lang: str
    original_lang: str
    published_at: datetime
    source: SourceBrief
    topics: list[str]
    hot_score: float
    cluster_id: Optional[str] = None


class NewsStreamResponse(BaseModel):
    items: list[NewsStreamItem]
    next_cursor: Optional[str] = None


class TopicBrief(BaseModel):
    key: str
    name: str
    confidence: float


class ClusterRelated(BaseModel):
    id: str
    title: str
    url: str
    source: SourceBrief


class ArticleDetail(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    content: Optional[str] = None
    url: str
    lang: str
    original_lang: str
    published_at: datetime
    source: SourceDetail
    topics: list[TopicBrief]
    hot_score: float
    cluster_id: Optional[str] = None
    cluster_related: list[ClusterRelated]
    # Field name must be "metadata" per spec; the ORM attribute is `meta`
    # (SQLAlchemy reserves "metadata"), so routers pass it explicitly.
    metadata: dict[str, Any]
