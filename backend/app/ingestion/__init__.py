"""Ingestion package: fetch raw articles from sources and normalize them.

Submodules:
- base: RawArticle dataclass + Fetcher protocol + normalization helpers.
- rss: RSS/Atom fetcher (feedparser).
- api_source: stub fetcher for partner JSON APIs (config via sources.meta).
- scraper_source: stub fetcher for external scraper actors (config via sources.meta).
- dedupe: dedupe/upsert logic per docs/05 §2.4.
- pipeline: ingest_source / ingest_all_active orchestration.
"""
from app.ingestion.base import Fetcher, RawArticle
from app.ingestion.pipeline import ingest_all_active, ingest_source

__all__ = ["Fetcher", "RawArticle", "ingest_all_active", "ingest_source"]
