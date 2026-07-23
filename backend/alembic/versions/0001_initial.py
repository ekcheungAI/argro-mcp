"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000

Creates the full schema per docs/02-data-model.md:
sources, articles, article_translations, topics, article_topics,
article_embeddings (pgvector), daily_insights. Also enables the
pgvector extension and creates GIN / HNSW indexes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # sources
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("lang", sa.Text(), nullable=False),
        sa.Column("homepage_url", sa.Text(), nullable=False),
        sa.Column("feed_url", sa.Text(), nullable=True),
        sa.Column("priority_weight", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sources_active", "sources", ["is_active"], unique=False)
    op.create_index("idx_sources_type", "sources", ["type"], unique=False)

    # articles
    op.create_table(
        "articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("original_lang", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hot_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("topics_cached", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'")),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "external_id", name="uq_articles_source_external_id"),
        sa.UniqueConstraint("source_id", "url", name="uq_articles_source_url"),
    )
    op.create_index("idx_articles_published_at_desc", "articles", [sa.text("published_at DESC")], unique=False)
    op.create_index("idx_articles_hot_score_desc", "articles", [sa.text("hot_score DESC")], unique=False)
    op.create_index(
        "idx_articles_topics_cached_gin",
        "articles",
        ["topics_cached"],
        unique=False,
        postgresql_using="gin",
    )

    # article_translations
    op.create_table(
        "article_translations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lang", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("translation_model", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id", "lang", name="uq_article_translations_article_lang"),
    )

    # topics
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    # article_topics
    op.create_table(
        "article_topics",
        sa.Column("article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"]),
        sa.PrimaryKeyConstraint("article_id", "topic_id"),
    )

    # article_embeddings
    op.create_table(
        "article_embeddings",
        sa.Column("article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.PrimaryKeyConstraint("article_id"),
    )
    # HNSW vector index (cosine distance)
    op.execute(
        "CREATE INDEX idx_article_embeddings_embedding_hnsw "
        "ON article_embeddings USING hnsw (embedding vector_cosine_ops);"
    )

    # daily_insights
    op.create_table(
        "daily_insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("lang", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("sections", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generated_from", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("type", "date", "lang", name="uq_daily_insights_type_date_lang"),
    )


def downgrade() -> None:
    op.drop_table("daily_insights")
    op.execute("DROP INDEX IF EXISTS idx_article_embeddings_embedding_hnsw;")
    op.drop_table("article_embeddings")
    op.drop_table("article_topics")
    op.drop_table("topics")
    op.drop_table("article_translations")
    op.drop_index("idx_articles_topics_cached_gin", table_name="articles")
    op.drop_index("idx_articles_hot_score_desc", table_name="articles")
    op.drop_index("idx_articles_published_at_desc", table_name="articles")
    op.drop_table("articles")
    op.drop_index("idx_sources_type", table_name="sources")
    op.drop_index("idx_sources_active", table_name="sources")
    op.drop_table("sources")
    op.execute("DROP EXTENSION IF EXISTS vector;")
