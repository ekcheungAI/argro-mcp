"""Idempotent seed script: topics + RSS sources.

Run with:  python -m app.seed
Safe to re-run: existing rows are detected (select-before-insert) and skipped.
"""
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Source, Topic

TOPICS: list[dict] = [
    {
        "key": "model_release",
        "name": "Model Release",
        "description": "New AI model launches and version upgrades (LLMs, vision, audio, etc.).",
    },
    {
        "key": "product_update",
        "name": "Product Update",
        "description": "Updates to AI-powered products, features, APIs, and developer tools.",
    },
    {
        "key": "industry_event",
        "name": "Industry Event",
        "description": "Conferences, keynotes, funding rounds, acquisitions, and other AI industry news.",
    },
    {
        "key": "policy",
        "name": "Policy & Regulation",
        "description": "Government policy, regulation, safety standards, and legal developments around AI.",
    },
    {
        "key": "research_paper",
        "name": "Research Paper",
        "description": "Notable AI research papers and preprints (e.g. arXiv) and benchmark results.",
    },
    {
        "key": "opinion_tutorial",
        "name": "Opinion & Tutorial",
        "description": "Opinion pieces, analysis, explainers, and hands-on tutorials about AI.",
    },
]

SOURCES: list[dict] = [
    {
        "name": "OpenAI Blog",
        "homepage_url": "https://openai.com/blog",
        "feed_url": "https://openai.com/blog/rss.xml",
        "priority_weight": 1.5,
    },
    {
        "name": "Anthropic News",
        "homepage_url": "https://www.anthropic.com/news",
        "feed_url": "https://www.anthropic.com/rss.xml",
        "priority_weight": 1.5,
    },
    {
        "name": "Google DeepMind Blog",
        "homepage_url": "https://deepmind.google/discover/blog/",
        "feed_url": "https://deepmind.google/blog/rss.xml",
        "priority_weight": 1.5,
    },
    {
        "name": "Hugging Face Blog",
        "homepage_url": "https://huggingface.co/blog",
        "feed_url": "https://huggingface.co/blog/feed.xml",
        "priority_weight": 1.5,
    },
    {
        "name": "arXiv cs.AI",
        "homepage_url": "https://arxiv.org/list/cs.AI/recent",
        "feed_url": "http://export.arxiv.org/rss/cs.AI",
        "priority_weight": 1.2,
    },
    {
        "name": "TechCrunch AI",
        "homepage_url": "https://techcrunch.com/category/artificial-intelligence/",
        "feed_url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "priority_weight": 1.0,
    },
    {
        "name": "The Verge AI",
        "homepage_url": "https://www.theverge.com/ai-artificial-intelligence",
        "feed_url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "priority_weight": 1.0,
    },
    {
        "name": "Ars Technica",
        "homepage_url": "https://arstechnica.com/",
        "feed_url": "https://feeds.arstechnica.com/arstechnica/index",
        "priority_weight": 1.0,
    },
    {
        "name": "MIT Technology Review",
        "homepage_url": "https://www.technologyreview.com/",
        "feed_url": "https://www.technologyreview.com/feed/",
        "priority_weight": 1.0,
    },
    {
        "name": "VentureBeat AI",
        "homepage_url": "https://venturebeat.com/ai/",
        "feed_url": "https://venturebeat.com/category/ai/feed/",
        "priority_weight": 1.0,
    },
]


def seed_topics(session) -> int:
    created = 0
    for data in TOPICS:
        exists = session.execute(select(Topic).where(Topic.key == data["key"])).scalar_one_or_none()
        if exists is None:
            session.add(Topic(**data))
            created += 1
    return created


def seed_sources(session) -> int:
    created = 0
    for data in SOURCES:
        exists = session.execute(select(Source).where(Source.name == data["name"])).scalar_one_or_none()
        if exists is None:
            session.add(Source(type="rss", lang="en", is_active=True, **data))
            created += 1
    return created


def main() -> None:
    with SessionLocal() as session:
        topics_created = seed_topics(session)
        sources_created = seed_sources(session)
        session.commit()
    print(f"Seed complete: {topics_created} topics, {sources_created} sources created (existing rows skipped).")


if __name__ == "__main__":
    main()
