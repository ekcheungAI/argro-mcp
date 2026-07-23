"""Ingestion pipeline orchestration (docs/05 §2).

``ingest_source`` picks a fetcher by ``source.type``, fetches raw articles,
normalizes them and dedupes/inserts into ``articles``. ``ingest_all_active``
runs it over every active source and aggregates per-source stats.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.ingestion.api_source import ApiSourceFetcher
from app.ingestion.rss import RssFetcher
from app.ingestion.scraper_source import ScraperSourceFetcher
from app.ingestion.dedupe import upsert_article
from app.models import Source

logger = logging.getLogger(__name__)

# source.type -> fetcher instance. Stateless fetchers are safe to share.
FETCHERS = {
    "rss": RssFetcher(),
    "api": ApiSourceFetcher(),
    "scraper": ScraperSourceFetcher(),
    # "social": not implemented yet -- logged + skipped below.
}


def ingest_source(session: Session, source: Source) -> dict:
    """Ingest a single source; returns a stats dict. Never raises."""
    stats = {
        "source_id": str(source.id),
        "source_name": source.name,
        "source_type": source.type,
        "fetched": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "error": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    fetcher = FETCHERS.get(source.type)
    if fetcher is None:
        logger.warning("No fetcher for source type %r (source %s); skipping", source.type, source.id)
        stats["error"] = f"unsupported type: {source.type}"
        return stats

    try:
        raw_articles = fetcher.fetch(source)
    except Exception as exc:  # fetchers should not raise, but belt & braces
        logger.exception("Fetcher crashed for source %s (%s)", source.id, source.name)
        stats["error"] = f"fetch failed: {exc}"
        return stats

    stats["fetched"] = len(raw_articles)
    # Bound work per run; feeds usually return far fewer items.
    for raw in raw_articles[: settings.ingestion_batch_size]:
        try:
            _article, created = upsert_article(session, source, raw)
        except Exception as exc:
            logger.warning(
                "Failed to upsert article %r from source %s: %s", raw.url, source.id, exc
            )
            session.rollback()
            stats["skipped"] += 1
            continue
        if created:
            stats["created"] += 1
        else:
            stats["updated"] += 1
    if len(raw_articles) > settings.ingestion_batch_size:
        stats["skipped"] += len(raw_articles) - settings.ingestion_batch_size

    try:
        session.commit()
    except Exception as exc:
        logger.exception("Commit failed for source %s (%s)", source.id, source.name)
        session.rollback()
        stats["error"] = f"commit failed: {exc}"
        stats["created"] = 0
        stats["updated"] = 0

    stats["finished_at"] = datetime.now(timezone.utc).isoformat()
    logger.info(
        "Ingested source %s (%s): fetched=%d created=%d updated=%d skipped=%d error=%s",
        source.id,
        source.name,
        stats["fetched"],
        stats["created"],
        stats["updated"],
        stats["skipped"],
        stats["error"],
    )
    return stats


def ingest_all_active(session: Session) -> list[dict]:
    """Ingest every active source; returns a list of per-source stats dicts."""
    sources = session.execute(
        select(Source).where(Source.is_active.is_(True)).order_by(Source.name)
    ).scalars().all()
    logger.info("Starting ingestion run over %d active sources", len(sources))

    all_stats: list[dict] = []
    for source in sources:
        all_stats.append(ingest_source(session, source))

    totals = {
        "sources": len(all_stats),
        "fetched": sum(s["fetched"] for s in all_stats),
        "created": sum(s["created"] for s in all_stats),
        "updated": sum(s["updated"] for s in all_stats),
        "skipped": sum(s["skipped"] for s in all_stats),
        "errors": sum(1 for s in all_stats if s["error"]),
    }
    logger.info("Ingestion run complete: %s", totals)
    return all_stats
