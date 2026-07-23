"""Worker entrypoint: ``python -m app.worker``.

Simple internal scheduler (loop + time.sleep), per docs/05 §7:

1. Every INGESTION_INTERVAL_MINUTES: run ingestion over all active sources.
2. After each ingestion run: enrichment batch in order
   lang_detect -> translate -> topics -> embed -> hot_score -> cluster.
3. Once per day (first run at/after 00:30 UTC): daily insight generation
   for each target language.

Graceful shutdown on SIGTERM/SIGINT: the current cycle finishes, then the
process exits.
"""
from __future__ import annotations

import logging
import signal
import time
from datetime import date, datetime, timezone

from app.config import settings
from app.db import SessionLocal
from app.enrichment import cluster, embed, hot_score, lang_detect, topics, translate
from app.ingestion.pipeline import ingest_all_active
from app.insights.generator import generate_daily_insight

logger = logging.getLogger(__name__)

DAILY_INSIGHT_HOUR_UTC = 0
DAILY_INSIGHT_MINUTE_UTC = 30

_running = True


def _handle_signal(signum, _frame) -> None:
    global _running
    logger.info("Received signal %d; finishing current cycle then shutting down", signum)
    _running = False


def run_enrichment_batch() -> None:
    """Run one enrichment pass; each step is isolated so one failure can't kill the batch."""
    steps = [
        ("lang_detect", lambda s: lang_detect.detect_pending(s)),
        ("translate", lambda s: translate.translate_pending(s)),
        ("topics", lambda s: topics.classify_pending(s)),
        ("embed", lambda s: embed.embed_pending(s)),
        ("hot_score", lambda s: hot_score.rescore_recent(s)),
        ("cluster", lambda s: cluster.cluster_recent(s)),
    ]
    with SessionLocal() as session:
        for name, step in steps:
            try:
                step(session)
            except Exception:
                logger.exception("Enrichment step %s failed; continuing with next step", name)
                session.rollback()


def run_ingestion_cycle() -> None:
    """One full cycle: ingestion + enrichment batch."""
    logger.info("=== Ingestion cycle starting ===")
    with SessionLocal() as session:
        try:
            ingest_all_active(session)
        except Exception:
            logger.exception("Ingestion run failed")
            session.rollback()
    run_enrichment_batch()
    logger.info("=== Ingestion cycle complete ===")


def run_daily_insights(target_day: date) -> None:
    """Generate the daily insight for every target language."""
    for lang in settings.target_langs_list:
        with SessionLocal() as session:
            try:
                generate_daily_insight(session, target_day, lang)
            except Exception:
                logger.exception("Daily insight generation failed for %s (%s)", target_day, lang)
                session.rollback()


def _due_for_daily_insight(now: datetime, last_run: date | None) -> bool:
    """True once per day, at/after 00:30 UTC, and not already done today."""
    if last_run == now.date():
        return False
    cutoff = now.replace(
        hour=DAILY_INSIGHT_HOUR_UTC, minute=DAILY_INSIGHT_MINUTE_UTC, second=0, microsecond=0
    )
    return now >= cutoff


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    interval_seconds = max(1, settings.ingestion_interval_minutes) * 60
    logger.info(
        "Worker starting: ingestion every %dmin, %d target langs, daily insight at %02d:%02d UTC",
        settings.ingestion_interval_minutes,
        len(settings.target_langs_list),
        DAILY_INSIGHT_HOUR_UTC,
        DAILY_INSIGHT_MINUTE_UTC,
    )

    last_insight_date: date | None = None
    next_cycle = 0.0  # run immediately on startup

    while _running:
        now_monotonic = time.monotonic()
        if now_monotonic >= next_cycle:
            try:
                run_ingestion_cycle()
            except Exception:
                logger.exception("Unhandled error in ingestion cycle")
            next_cycle = time.monotonic() + interval_seconds

        now_utc = datetime.now(timezone.utc)
        if _due_for_daily_insight(now_utc, last_insight_date):
            run_daily_insights(now_utc.date())
            last_insight_date = now_utc.date()

        # Sleep in small slices so SIGTERM is handled promptly.
        wake_at = min(next_cycle, time.monotonic() + 5.0)
        while _running and time.monotonic() < wake_at:
            time.sleep(0.5)

    logger.info("Worker shut down cleanly")


if __name__ == "__main__":
    main()
