"""sources table model."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)  # rss | api | scraper | social
    lang: Mapped[str] = mapped_column(Text, nullable=False)
    homepage_url: Mapped[str] = mapped_column(Text, nullable=False)
    feed_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1.0")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_sources_active", "is_active"),
        Index("idx_sources_type", "type"),
    )
