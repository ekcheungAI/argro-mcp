"""Pydantic response schemas, aligned field-by-field with docs/03-http-api-spec.md."""
from app.schemas.insights import InsightResponse, InsightSection
from app.schemas.meta import SourceMeta, SourcesResponse, TopicMeta, TopicsResponse
from app.schemas.news import (
    ArticleDetail,
    ClusterRelated,
    NewsStreamItem,
    NewsStreamResponse,
    SourceBrief,
    SourceDetail,
    TopicBrief,
)

__all__ = [
    "ArticleDetail",
    "ClusterRelated",
    "InsightResponse",
    "InsightSection",
    "NewsStreamItem",
    "NewsStreamResponse",
    "SourceBrief",
    "SourceDetail",
    "SourceMeta",
    "SourcesResponse",
    "TopicBrief",
    "TopicMeta",
    "TopicsResponse",
]
