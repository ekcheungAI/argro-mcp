"""Response schemas for /meta/* endpoints (docs/03-http-api-spec.md §2.5-2.6)."""
from typing import Optional

from pydantic import BaseModel


class SourceMeta(BaseModel):
    id: str
    name: str
    type: str
    lang: str
    homepage_url: str
    feed_url: Optional[str] = None
    priority_weight: float
    is_active: bool


class SourcesResponse(BaseModel):
    sources: list[SourceMeta]


class TopicMeta(BaseModel):
    key: str
    name: str
    description: Optional[str] = None


class TopicsResponse(BaseModel):
    topics: list[TopicMeta]
