# HTTP API Specification (v1)

Base URL: `https://api.ai-news-platform.com/v1`

All responses are JSON with `application/json` content type.

## 1. Authentication

For now, assume:
- Private deployments: simple API key via header `X-API-Key: <token>`.
- Public read-only endpoints MAY be exposed without auth in early stages.

## 2. Endpoints

### 2.1 GET /news/stream

Returns a paginated list of news articles matching filters.

**Query parameters:**

- `from` (string, optional): ISO8601 datetime or `YYYY-MM-DD`.
- `to` (string, optional): same as above. If omitted, defaults to now.
- `lang` (string, optional): desired language code (e.g. `en`, `zh-TW`).
  - If present, server should return translated fields when available, fallback to original.
- `topic` (string, optional): topic key or comma-separated list.
- `source` (string, optional): source id or comma-separated list.
- `q` (string, optional): search query for full-text / semantic search.
- `sort` (string, optional): `time_desc` | `hot_desc`. Default: `time_desc`.
- `limit` (int, optional): default 50, max 200.
- `cursor` (string, optional): cursor for pagination.

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "title": "string",
      "summary": "string or null",
      "url": "string",
      "lang": "string",          
      "original_lang": "string",
      "published_at": "2026-07-23T08:00:00Z",
      "source": {
        "id": "string",
        "name": "string"
      },
      "topics": ["model_release", "product_update"],
      "hot_score": 0.93,
      "cluster_id": "uuid or null"
    }
  ],
  "next_cursor": "string or null"
}
```

---

### 2.2 GET /news/hot

Returns “hot” articles for a given date.

**Query parameters:**

- `date` (string, optional): `YYYY-MM-DD`. Defaults to today (UTC).
- `lang` (string, optional): desired language (same behavior as above).
- `topic` (string, optional).
- `limit` (int, optional): default 30, max 100.

**Response:** same structure as `/news/stream`, filtered and sorted by `hot_score`.

---

### 2.3 GET /news/{id}

Returns detailed information about a single article.

**Path parameter:**

- `id` (string, required): article id.

**Query parameters:**

- `lang` (string, optional): desired language.

**Response:**

```json
{
  "id": "uuid",
  "title": "string",
  "summary": "string or null",
  "content": "string or null",
  "url": "string",
  "lang": "string",
  "original_lang": "string",
  "published_at": "2026-07-23T08:00:00Z",
  "source": {
    "id": "string",
    "name": "string",
    "homepage_url": "string"
  },
  "topics": [
    {
      "key": "model_release",
      "name": "Model Release",
      "confidence": 0.92
    }
  ],
  "hot_score": 0.93,
  "cluster_id": "uuid or null",
  "cluster_related": [
    {
      "id": "uuid",
      "title": "string",
      "url": "string",
      "source": { "id": "string", "name": "string" }
    }
  ],
  "metadata": {}
}
```

---

### 2.4 GET /insights/daily

Returns daily or weekly insight document.

**Query parameters:**

- `type` (string, optional): `daily` | `weekly`. Default: `daily`.
- `date` (string, optional): `YYYY-MM-DD`. If omitted, use latest available.
- `lang` (string, optional): desired language.

**Response:**

```json
{
  "id": "uuid",
  "type": "daily",
  "date": "2026-07-23",
  "lang": "en",
  "title": "2026-07-23 AI Highlights",
  "summary": "string",
  "sections": [
    {
      "section_title": "Model Releases",
      "content": "string",
      "articles": ["article_id_1", "article_id_2"]
    }
  ]
}
```

---

### 2.5 GET /meta/sources

Returns list of active sources.

**Response:**

```json
{
  "sources": [
    {
      "id": "string",
      "name": "string",
      "type": "rss",
      "lang": "en",
      "homepage_url": "string",
      "feed_url": "string or null",
      "priority_weight": 1.0,
      "is_active": true
    }
  ]
}
```

---

### 2.6 GET /meta/topics

Returns topic taxonomy.

**Response:**

```json
{
  "topics": [
    {
      "key": "model_release",
      "name": "Model Release",
      "description": "New AI model releases and major upgrades."
    }
  ]
}
```
