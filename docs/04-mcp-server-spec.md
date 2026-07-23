# MCP Server Specification – ai-news-mcp-server

We provide an MCP server that exposes news data to AI assistants via tools.

The MCP server SHOULD be stateless and talk to the backend HTTP API defined in 03-HTTP-API-SPEC.md.

## 1. Server Identity

- Name: `ai-news-mcp-server`
- Description: “Multi-source AI news and insights for agents: hot list, search, and structured daily briefs.”

## 2. Tools

### 2.1 get_daily_hot

**Purpose:** Fetch the hot AI news list for a specific date and language.

**Input schema:**

```json
{
  "type": "object",
  "properties": {
    "date": { "type": "string", "description": "YYYY-MM-DD, defaults to today", "nullable": true },
    "lang": { "type": "string", "description": "Target language code, e.g. en, zh-TW", "nullable": true },
    "limit": { "type": "integer", "description": "Max items", "default": 30 }
  }
}
```

**Output schema:**

- Directly based on `GET /news/hot` response (`items[]`).

---

### 2.2 search_news

**Purpose:** Search AI news by natural language query and optional filters.

**Input schema:**

```json
{
  "type": "object",
  "properties": {
    "query": { "type": "string", "description": "Natural language query", "minLength": 1 },
    "lang": { "type": "string", "nullable": true },
    "from": { "type": "string", "nullable": true, "description": "YYYY-MM-DD or ISO8601" },
    "to": { "type": "string", "nullable": true },
    "topic": { "type": "string", "nullable": true },
    "limit": { "type": "integer", "default": 20 }
  },
  "required": ["query"]
}
```

**Behavior:**

- Map to `GET /news/stream` with:
  - `q = query`, `lang`, `from`, `to`, `topic`, `limit`.
- Return:
  - List of article summaries (same structure as `/news/stream.items`).

---

### 2.3 get_article_detail

**Purpose:** Get full detail for a selected article.

**Input schema:**

```json
{
  "type": "object",
  "properties": {
    "id": { "type": "string", "description": "Article id" },
    "lang": { "type": "string", "nullable": true }
  },
  "required": ["id"]
}
```

**Output schema:**

- Based on `GET /news/{id}` response.

---

### 2.4 get_insight

**Purpose:** Fetch structured daily/weekly insights.

**Input schema:**

```json
{
  "type": "object",
  "properties": {
    "type": { "type": "string", "enum": ["daily", "weekly"], "default": "daily" },
    "date": { "type": "string", "nullable": true, "description": "YYYY-MM-DD; if null, latest" },
    "lang": { "type": "string", "nullable": true }
  }
}
```

**Output schema:**

- Based on `GET /insights/daily` response.

---

### 2.5 get_trends (optional)

**Purpose:** Provide time-series / aggregate stats for trends.

We can define this later when we add analytics.
