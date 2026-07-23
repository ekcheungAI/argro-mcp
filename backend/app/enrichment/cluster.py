"""Event clustering (docs/05 §5) -- minimal viable version.

Goal: articles about the same event (published within a 24h window of each
other) share a ``cluster_id``.

Strategy (in priority order):
1. If embeddings exist (pgvector), group pairs whose cosine distance is below
   EMBEDDING_COSINE_THRESHOLD. Cosine similarity is computed in Python for
   the small recent window; once the article volume grows this should be
   replaced by a pgvector ``embedding <=> embedding`` ANN query.
2. Otherwise fall back to a title token-overlap (Jaccard) heuristic.

Union-find over the matched pairs yields connected components; components
with >= 2 members get a shared cluster_id (reused from a member that already
had one, else a fresh uuid). Singletons keep cluster_id = NULL.
"""
from __future__ import annotations

import logging
import math
import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Article, ArticleEmbedding

logger = logging.getLogger(__name__)

CLUSTER_WINDOW_HOURS = 24
EMBEDDING_COSINE_THRESHOLD = 0.15  # cosine distance; smaller = more similar
TITLE_JACCARD_THRESHOLD = 0.5

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    "a an the and or of to in for on with by is are was were be been at from as it its "
    "this that new says say will how what why".split()
)


def cluster_recent(session: Session, hours: int = CLUSTER_WINDOW_HOURS) -> int:
    """Cluster active articles published within the window. Returns # clustered."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles = (
        session.execute(
            select(Article)
            .where(Article.status == "active", Article.published_at >= cutoff)
            .order_by(Article.published_at.desc())
        )
        .scalars()
        .all()
    )
    if len(articles) < 2:
        return 0

    embeddings = _load_embeddings(session, [a.id for a in articles])
    parent = {a.id: a.id for a in articles}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    title_tokens = {a.id: _title_tokens(a.title) for a in articles}
    for i in range(len(articles)):
        for j in range(i + 1, len(articles)):
            a, b = articles[i], articles[j]
            if _is_match(a, b, embeddings, title_tokens):
                union(a.id, b.id)

    # Assign cluster ids to multi-article components.
    components: dict[uuid.UUID, list[Article]] = {}
    for article in articles:
        components.setdefault(find(article.id), []).append(article)

    clustered = 0
    for members in components.values():
        if len(members) < 2:
            continue
        cluster_id = next((m.cluster_id for m in members if m.cluster_id), None) or uuid.uuid4()
        for member in members:
            if member.cluster_id != cluster_id:
                member.cluster_id = cluster_id
                clustered += 1

    if clustered:
        session.commit()
    logger.info(
        "Clustering: %d articles in window, %d assigned to %d clusters (mode=%s)",
        len(articles),
        clustered,
        sum(1 for m in components.values() if len(members) >= 2),
        "embedding" if embeddings else "title-overlap",
    )
    return clustered


# ---------------------------------------------------------------------- #
# internals
# ---------------------------------------------------------------------- #


def _load_embeddings(session: Session, article_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[float]]:
    rows = (
        session.execute(select(ArticleEmbedding).where(ArticleEmbedding.article_id.in_(article_ids)))
        .scalars()
        .all()
    )
    return {row.article_id: list(row.embedding) for row in rows}


def _is_match(a: Article, b: Article, embeddings: dict, title_tokens: dict) -> bool:
    va, vb = embeddings.get(a.id), embeddings.get(b.id)
    if va is not None and vb is not None:
        return _cosine_distance(va, vb) <= EMBEDDING_COSINE_THRESHOLD
    return _jaccard(title_tokens[a.id], title_tokens[b.id]) >= TITLE_JACCARD_THRESHOLD


def _cosine_distance(va: list[float], vb: list[float]) -> float:
    dot = sum(x * y for x, y in zip(va, vb))
    na = math.sqrt(sum(x * x for x in va))
    nb = math.sqrt(sum(y * y for y in vb))
    if na == 0 or nb == 0:
        return 1.0
    return 1.0 - dot / (na * nb)


def _title_tokens(title: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(title.lower()) if t not in _STOPWORDS and len(t) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
