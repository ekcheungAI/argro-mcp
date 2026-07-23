"""articles table model.

Note: ``metadata`` is a reserved attribute in SQLAlchemy's declarative API,
so the Python attribute is named ``meta`` while the database column remains
``metadata`` per the data-model spec.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    original_lang: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hot_score: Mapped[float] = mapped_column(Float, nullable=False, default=0, server_default="0")
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    topics_cached: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default="{}"
    )
    # DB column name is "metadata" (spec); Python attribute renamed to "meta"
    # because Declarative reserves "metadata".
    meta: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active", server_default="active")

    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_articles_source_external_id"),
        UniqueConstraint("source_id", "url", name="uq_articles_source_url"),
        Index("idx_articles_published_at_desc", published_at.desc()),
        Index("idx_articles_hot_score_desc", hot_score.desc()),
        Index("idx_articles_topics_cached_gin", "topics_cached", postgresql_using="gin"),
    )
