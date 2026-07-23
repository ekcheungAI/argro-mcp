"""article_topics table model."""
import uuid

from sqlalchemy import Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ArticleTopic(Base):
    __tablename__ = "article_topics"

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("articles.id"), primary_key=True
    )
    topic_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("topics.id"), primary_key=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0, server_default="0")
