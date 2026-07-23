"""All ORM models, imported here so Alembic sees the full metadata."""
from app.models.article import Article
from app.models.article_embedding import ArticleEmbedding
from app.models.article_topic import ArticleTopic
from app.models.article_translation import ArticleTranslation
from app.models.daily_insight import DailyInsight
from app.models.source import Source
from app.models.topic import Topic

__all__ = [
    "Article",
    "ArticleEmbedding",
    "ArticleTopic",
    "ArticleTranslation",
    "DailyInsight",
    "Source",
    "Topic",
]
