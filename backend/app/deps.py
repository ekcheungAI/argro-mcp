"""Shared FastAPI dependencies and helpers.

- API-key auth (optional per docs/03 §1: public read-only in early stages).
- Keyset (cursor) pagination helpers.
- Language resolution (translation with fallback to original).
- Date/datetime query-param parsing.
"""
import base64
import binascii
import uuid
from datetime import date, datetime, time, timezone
from typing import Any, Mapping, Optional

from fastapi import Header, HTTPException
from sqlalchemy import Select, and_, or_

from app.config import settings
from app.models.article import Article
from app.models.article_translation import ArticleTranslation

SORT_TIME_DESC = "time_desc"
SORT_HOT_DESC = "hot_desc"


# ---------------------------------------------------------------------------
# Auth (docs/03 §1)
# ---------------------------------------------------------------------------

async def optional_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
    """Validate the X-API-Key header only when an API key is configured.

    If ``settings.api_key`` is unset the deployment is public read-only and
    every request passes (docs/03 §1). Otherwise a missing/wrong key -> 401.
    """
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ---------------------------------------------------------------------------
# Cursor (keyset) pagination
# ---------------------------------------------------------------------------

def _format_sort_value(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return repr(float(value))


def encode_cursor(sort_value: Any, row_id: uuid.UUID) -> str:
    """Encode ``"{sort_value}|{id}"`` as URL-safe base64 (padding stripped)."""
    raw = f"{_format_sort_value(sort_value)}|{row_id}"
    return base64.urlsafe_b64encode(raw.encode("ascii")).decode("ascii").rstrip("=")


def decode_cursor(cursor: str, sort: str) -> tuple[Any, uuid.UUID]:
    """Decode a cursor produced by :func:`encode_cursor`.

    ``sort`` selects how the sort value is parsed (``time_desc`` -> datetime,
    ``hot_desc`` -> float). Raises HTTP 400 on any malformed cursor.
    """
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("ascii")
        sort_raw, _, id_raw = raw.rpartition("|")
        if not sort_raw or not id_raw:
            raise ValueError("missing separator")
        row_id = uuid.UUID(id_raw)
        if sort == SORT_HOT_DESC:
            sort_value: Any = float(sort_raw)
        else:
            sort_value = datetime.fromisoformat(sort_raw)
            if sort_value.tzinfo is None:
                sort_value = sort_value.replace(tzinfo=timezone.utc)
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid cursor: {exc}") from exc
    return sort_value, row_id


def apply_cursor(query: Select, cursor: str, sort: str) -> Select:
    """Apply keyset pagination to a DESC-ordered query (no OFFSET).

    Rows are ordered by ``(sort_column DESC, id DESC)``; the cursor selects the
    rows strictly after the cursor position.
    """
    sort_value, row_id = decode_cursor(cursor, sort)
    sort_col = Article.hot_score if sort == SORT_HOT_DESC else Article.published_at
    return query.where(
        or_(
            sort_col < sort_value,
            and_(sort_col == sort_value, Article.id < row_id),
        )
    )


def order_by_sort(query: Select, sort: str) -> Select:
    """Deterministic DESC ordering matching :func:`apply_cursor`."""
    sort_col = Article.hot_score if sort == SORT_HOT_DESC else Article.published_at
    return query.order_by(sort_col.desc(), Article.id.desc())


# ---------------------------------------------------------------------------
# Date / datetime query params (docs/03: YYYY-MM-DD or ISO8601)
# ---------------------------------------------------------------------------

def parse_datetime_param(value: str, *, param: str, end_of_day: bool = False) -> datetime:
    """Parse a query param that may be ``YYYY-MM-DD`` or full ISO8601.

    Date-only values mean start-of-day UTC (``end_of_day=True`` -> end-of-day
    UTC, so ``to=2026-07-23`` includes the whole day). Invalid input -> 400.
    """
    try:
        if len(value) == 10:
            d = date.fromisoformat(value)
            t = time.max if end_of_day else time.min
            return datetime.combine(d, t, tzinfo=timezone.utc)
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid '{param}' parameter: {exc}") from exc


def parse_date_param(value: str, *, param: str) -> date:
    """Parse a strict ``YYYY-MM-DD`` query param. Invalid input -> 400."""
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid '{param}' parameter: {exc}") from exc


# ---------------------------------------------------------------------------
# Language resolution (translation with fallback)
# ---------------------------------------------------------------------------

def resolve_lang(
    article: Article,
    translations_map: Mapping[uuid.UUID, ArticleTranslation],
    lang: Optional[str],
) -> dict[str, Any]:
    """Pick translated title/summary/content when available, else original.

    Response ``lang`` is the requested language when a translation exists,
    otherwise the article's ``original_lang`` (docs/03 §2.1).
    """
    translation = translations_map.get(article.id) if lang else None
    if translation is not None:
        return {
            "title": translation.title,
            "summary": translation.summary,
            "content": translation.content,
            "lang": lang,
        }
    return {
        "title": article.title,
        "summary": article.summary,
        "content": article.content,
        "lang": article.original_lang,
    }
