"""Schema-level contract tests.

Each fixture below is copied from the example JSON in
docs/03-http-api-spec.md; tests assert the Pydantic response models accept the
spec shape and serialize with exactly the same key set (per field, per level).
Also covers cursor pagination helpers and language fallback — none of these
need a database.
"""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.deps import decode_cursor, encode_cursor, resolve_lang
from app.schemas.insights import InsightResponse
from app.schemas.meta import SourcesResponse, TopicsResponse
from app.schemas.news import ArticleDetail, NewsStreamResponse

# --- Example payloads from docs/03-http-api-spec.md -------------------------

STREAM_EXAMPLE = {
    "items": [
        {
            "id": "3f6b2c44-1e2a-4b1c-9a0d-1234567890ab",
            "title": "string",
            "summary": "string or null",
            "url": "string",
            "lang": "string",
            "original_lang": "string",
            "published_at": "2026-07-23T08:00:00Z",
            "source": {"id": "string", "name": "string"},
            "topics": ["model_release", "product_update"],
            "hot_score": 0.93,
            "cluster_id": "9f6b2c44-1e2a-4b1c-9a0d-1234567890ab",
        }
    ],
    "next_cursor": "string or null",
}

ARTICLE_DETAIL_EXAMPLE = {
    "id": "3f6b2c44-1e2a-4b1c-9a0d-1234567890ab",
    "title": "string",
    "summary": "string or null",
    "content": "string or null",
    "url": "string",
    "lang": "string",
    "original_lang": "string",
    "published_at": "2026-07-23T08:00:00Z",
    "source": {"id": "string", "name": "string", "homepage_url": "string"},
    "topics": [{"key": "model_release", "name": "Model Release", "confidence": 0.92}],
    "hot_score": 0.93,
    "cluster_id": "9f6b2c44-1e2a-4b1c-9a0d-1234567890ab",
    "cluster_related": [
        {
            "id": "1a6b2c44-1e2a-4b1c-9a0d-1234567890ab",
            "title": "string",
            "url": "string",
            "source": {"id": "string", "name": "string"},
        }
    ],
    "metadata": {},
}

INSIGHT_EXAMPLE = {
    "id": "3f6b2c44-1e2a-4b1c-9a0d-1234567890ab",
    "type": "daily",
    "date": "2026-07-23",
    "lang": "en",
    "title": "2026-07-23 AI Highlights",
    "summary": "string",
    "sections": [
        {
            "section_title": "Model Releases",
            "content": "string",
            "articles": ["article_id_1", "article_id_2"],
        }
    ],
}

SOURCES_EXAMPLE = {
    "sources": [
        {
            "id": "string",
            "name": "string",
            "type": "rss",
            "lang": "en",
            "homepage_url": "string",
            "feed_url": "string or null",
            "priority_weight": 1.0,
            "is_active": True,
        }
    ]
}

TOPICS_EXAMPLE = {
    "topics": [
        {
            "key": "model_release",
            "name": "Model Release",
            "description": "New AI model releases and major upgrades.",
        }
    ]
}


def _assert_keys(data: dict, example: dict, path: str = "") -> None:
    assert set(data.keys()) == set(example.keys()), (
        f"key mismatch at {path or '<root>'}: "
        f"extra={set(data) - set(example)}, missing={set(example) - set(data)}"
    )
    for key, ex_val in example.items():
        val = data[key]
        loc = f"{path}.{key}" if path else key
        if isinstance(ex_val, dict):
            _assert_keys(val, ex_val, loc)
        elif isinstance(ex_val, list) and ex_val and isinstance(ex_val[0], dict):
            assert isinstance(val, list) and val, f"{loc} should be a non-empty list"
            for item in val:
                _assert_keys(item, ex_val[0], loc)


@pytest.mark.parametrize(
    ("model", "example"),
    [
        (NewsStreamResponse, STREAM_EXAMPLE),
        (ArticleDetail, ARTICLE_DETAIL_EXAMPLE),
        (InsightResponse, INSIGHT_EXAMPLE),
        (SourcesResponse, SOURCES_EXAMPLE),
        (TopicsResponse, TOPICS_EXAMPLE),
    ],
    ids=["news_stream", "article_detail", "insight", "sources", "topics"],
)
def test_response_model_matches_spec_example(model, example):
    parsed = model.model_validate(example)
    dumped = parsed.model_dump(mode="json")
    # Round-trip: re-validate the serialized form.
    model.model_validate(dumped)
    _assert_keys(dumped, example)


def test_nullable_fields_accept_null():
    item = dict(STREAM_EXAMPLE["items"][0], summary=None, cluster_id=None)
    resp = NewsStreamResponse.model_validate({"items": [item], "next_cursor": None})
    assert resp.items[0].summary is None
    assert resp.items[0].cluster_id is None
    assert resp.next_cursor is None

    detail = ArticleDetail.model_validate(
        dict(ARTICLE_DETAIL_EXAMPLE, summary=None, content=None, cluster_id=None)
    )
    assert detail.summary is None and detail.content is None and detail.cluster_id is None

    src = SourcesResponse.model_validate(
        {"sources": [dict(SOURCES_EXAMPLE["sources"][0], feed_url=None)]}
    )
    assert src.sources[0].feed_url is None

    topics = TopicsResponse.model_validate(
        {"topics": [dict(TOPICS_EXAMPLE["topics"][0], description=None)]}
    )
    assert topics.topics[0].description is None


# --- Cursor helpers ----------------------------------------------------------

def test_cursor_roundtrip_time_desc():
    row_id = uuid.uuid4()
    ts = datetime(2026, 7, 23, 8, 0, 0, tzinfo=timezone.utc)
    cursor = encode_cursor(ts, row_id)
    sort_value, decoded_id = decode_cursor(cursor, "time_desc")
    assert decoded_id == row_id
    assert sort_value == ts


def test_cursor_roundtrip_hot_desc():
    row_id = uuid.uuid4()
    cursor = encode_cursor(0.93, row_id)
    sort_value, decoded_id = decode_cursor(cursor, "hot_desc")
    assert decoded_id == row_id
    assert sort_value == pytest.approx(0.93)


@pytest.mark.parametrize("bad", ["!!!not-base64!!!", "aGVsbG8", "", "e30="])
def test_decode_cursor_invalid_raises_400(bad):
    with pytest.raises(HTTPException) as exc_info:
        decode_cursor(bad, "time_desc")
    assert exc_info.value.status_code == 400


# --- Language fallback -------------------------------------------------------

def _fake_article(**overrides):
    base = dict(
        id=uuid.uuid4(),
        title="Original title",
        summary="Original summary",
        content="Original content",
        original_lang="en",
    )
    return SimpleNamespace(**(base | overrides))


def test_resolve_lang_uses_translation_when_present():
    article = _fake_article()
    translation = SimpleNamespace(title="Translated", summary="T summary", content="T content")
    resolved = resolve_lang(article, {article.id: translation}, "zh-TW")
    assert resolved == {
        "title": "Translated",
        "summary": "T summary",
        "content": "T content",
        "lang": "zh-TW",
    }


def test_resolve_lang_falls_back_to_original():
    article = _fake_article()
    # No translation for requested lang -> original fields, lang = original_lang.
    resolved = resolve_lang(article, {}, "zh-TW")
    assert resolved["title"] == "Original title"
    assert resolved["lang"] == "en"
    # No lang requested at all -> also original.
    resolved = resolve_lang(article, {}, None)
    assert resolved["lang"] == "en"
