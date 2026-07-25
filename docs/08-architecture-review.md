# AIGRO / argro-mcp — Architecture & MCP Arrangement Review (Confirmation Study Pack)

> **Purpose**: for a third-party reviewer (human or AI agent) to confirm whether the overall arrangement of the "AI news aggregation platform + MCP server" is sound, whether the deployment topology is correct, and how external projects should integrate.
> Repo: https://github.com/ekcheungAI/argro-mcp (branch: `main`)
> Authoritative specs: `docs/01`-`07` in repo (product, data model, HTTP API, MCP spec, ingestion, frontend UX, Zeabur infra)
> Date: 2026-07-24 | Status: code complete + local E2E verified, **not yet deployed**

---

## 1. One-line Summary

A self-hosted "AI news data infra layer": multi-source ingestion -> PostgreSQL storage -> FastAPI public read-only API -> a **stateless MCP server** on top, so any AI agent (Claude / Kimi / Cursor / the owner's other projects) can ask in natural language "what happened in AI today".

---

## 2. System Overview

```
                        +---------------------------------------------+
                        |                 Zeabur Project              |
                        |                                             |
  RSS / API / Scraper   |   +--------+      +------------------+      |
  (10 seed sources) ----+-->| worker |----->| PostgreSQL 16     |     |
                        |   |(ingest |      | + pgvector        |     |
                        |   |+enrich)|      | 8 tables          |     |
                        |   +--------+      +--------^---------+      |
                        |                            | SQLAlchemy     |
                        |                     +------+-------+        |
                        |                     | backend      |        |
                        |                     | FastAPI :8000|        |
                        |                     | /healthz     |        |
                        |                     +--+--------+--+        |
                        |              HTTP      |        | HTTP      |
                        |              +---------v--+  +--v---------+ |
                        |              | mcp-server |  | frontend   | |
                        |              | FastMCP    |  | Next.js    | |
                        |              | :8100 /mcp |  | :3000      | |
                        |              +-----+------+  +----+-------+ |
                        +--------------------|--------------|--------+
                                             |              |
                              MCP clients <--+              +--> users' browsers
                    (Claude / Kimi / Cursor /
                     other projects' agents)
```

**Key design principle**: the MCP server is a **stateless thin wrapper** — it only calls the backend API over HTTP and **never touches the DB directly**. Benefit: the backend is the single data gateway; the MCP server can be scaled / restarted / replaced at any time with no state to migrate.

---

## 3. Component Responsibilities

| Component | Tech | Responsibility | Public? |
|---|---|---|---|
| `backend` | FastAPI + SQLAlchemy 2.0 + Alembic | 6 read-only REST endpoints; ORM + migrations | Yes (API consumers) |
| `worker` | same image as backend, `python -m app.worker` | ingestion every 15 min (RSS->normalize->dedupe) + enrichment (lang detect->translate->topics->embedding->hot score->clustering) + daily insight at 00:30 UTC | No (internal) |
| `mcp-server` | Python `mcp` SDK FastMCP, streamable HTTP | 4 tools, thin wrapper around backend API | **Yes (core deliverable)** |
| `frontend` | Next.js 15 + Tailwind | `/` `/all` `/insights` `/insights/[date]` `/developers` | Yes |
| `postgres` | pgvector/pgvector:pg16 | storage + vector search | No |

---

## 4. MCP Server Details (review focus)

**Identity**: name `ai-news-mcp-server`; transport = **streamable HTTP** (path `/mcp`); `stateless_http=True`, `json_response=True`.

### 4.1 Tools (input schemas strictly per `docs/04`)

| Tool | Params | Backend call | Purpose |
|---|---|---|---|
| `get_daily_hot` | `date?` `lang?` `limit=30` | `GET /news/hot` | Hot AI news for today / a given date |
| `search_news` | `query*` `lang?` `from?` `to?` `topic?` `limit=20` | `GET /news/stream` (`q=query`) | Natural-language search + filters |
| `get_article_detail` | `id*` `lang?` | `GET /news/{id}` | Full article + related cluster |
| `get_insight` | `type=daily|weekly` `date?` `lang?` | `GET /insights/daily` | Structured daily/weekly brief |

`get_trends` intentionally not implemented (spec marks optional/later).

### 4.2 Three ways external projects integrate

**(A) MCP client direct connect** (Claude Desktop / Cursor / Kimi etc.):
```json
{
  "mcpServers": {
    "ai-news": { "url": "https://<mcp-server>.zeabur.app/mcp" }
  }
}
```

**(B) Owner's project agents via official SDK**:
```python
from mcp.client.streamable_http import streamablehttp_client
# connect https://<mcp-server>.zeabur.app/mcp -> list_tools / call_tool
```

**(C) Bypass MCP, consume REST API directly** (dashboards, cron jobs, site backends):
```
GET https://<backend>.zeabur.app/news/hot?lang=zh-TW
GET https://<backend>.zeabur.app/insights/daily
```

> In short: MCP is the "agent-friendly entry", REST API is the "programmatic entry" — both share the same backend. This is the core of the whole arrangement.

---

## 5. Data Flow

```
worker (every 15 min):
  sources(is_active) -> fetcher(rss/api/scraper) -> RawArticle
  -> dedupe: (source_id, external_id) -> fallback (source_id, url)
  -> insert/update articles

enrichment batch:
  lang_detect -> translate*(en/zh-TW) -> topics(*LLM or keyword fallback)
  -> embed* -> hot_score(priority_weight x time decay) -> cluster

daily 00:30 UTC:
  generate_daily_insight(*LLM or fallback) -> daily_insights table

* = requires MOONSHOT_API_KEY; without key everything gracefully no-ops / falls back, system still runs
```

---

## 6. Zeabur Deployment Topology (planned, not executed)

| Service | Source | Port | Key env | Bind domain? |
|---|---|---|---|---|
| postgres | Zeabur prebuilt PostgreSQL | 5432 internal | `POSTGRES_DB=argro`; needs `CREATE EXTENSION vector` (migration includes it) | No |
| backend | CLI deploy `infra/Dockerfile.backend` | 8000 | `DATABASE_URL` (`postgresql+psycopg://...`) | Yes (API) |
| migrate | one-shot job (same backend image) | — | same | No |
| worker | same backend image, cmd override | — | same + `MOONSHOT_API_KEY` | No |
| mcp-server | `infra/Dockerfile.mcp` | 8100 | `MCP_BACKEND_URL=http://backend:8000` (or internal DNS) | **Yes** (MCP clients) |
| frontend | `infra/Dockerfile.frontend` | 3000 | `NEXT_PUBLIC_API_BASE_URL` (build-time) | Yes |

Detailed steps in repo `infra/ZEABUR-SETUP.md`; full env table in `infra/ENVIRONMENT-VARS.md`.

---

## 7. Verified / Not Yet Verified

**Verified (local, real PostgreSQL 15 + pgvector E2E)**:
- Alembic migration creates 8 tables + all constraints/indexes (GIN, HNSW)
- Seed 6 topics + 10 RSS sources (idempotent)
- All 6 endpoints curl-tested (cursor pagination, lang fallback, 422/404 boundaries)
- MCP server E2E: all 4 tools called via official client
- Dedupe adversarial tests; pytest 16/16; frontend `next build` + lint all green

**Not yet verified (test first after deployment)**:
- Docker build (no docker locally) — Zeabur build is the first real test
- Real RSS fetch speed / individual feed URL validity (worker skips + logs bad feeds)
- Moonshot LLM enrichment (needs key)
- Zeabur internal service-to-service networking (`MCP_BACKEND_URL` internal vs public address)
- Worker long-run stability

---

## 8. Decision Checklist for Reviewer

| # | Decision | Current state | Question |
|---|---|---|---|
| 1 | API has no `/v1` prefix (03 spec base URL mentions `/v1`) | Deliberately omitted, noted in code | Accept or add prefix? |
| 2 | Auth off by default (public read-only; `X-API-Key` check activates only when `API_KEY` is set) | Per 03 section 1 early-stage approach | Must auth be on before going public? |
| 3 | MCP server publicly exposed, no auth | Same as above | Acceptable? (abuse risk = read-only, but consumes backend resources) |
| 4 | Translation target langs `en, zh-TW` | env `TARGET_LANGS` configurable | Enough? (owner is HK creator; may want zh-CN / ja) |
| 5 | Seed sources: only 10 English RSS | Can add later | Add Chinese/HK sources? (36kr, Solidot, Synced etc.) |
| 6 | `get_trends` tool not built | spec says later | When? |
| 7 | GitHub push -> auto redeploy | Requires installing Zeabur GitHub App in dashboard (OAuth, not possible via API) | Install or not? Otherwise manual CLI deploy each time |
| 8 | Custom domain (e.g. `news.ekcheung.com`) | Not done | Free `*.zeabur.app` or own domain? |
| 9 | Repo currently public | No secrets inside | Keep public or go private? |
| 10 | Scaling: backend 1 replica, worker 1 | Enough for v1 | Any expected traffic needing more from day one? |

---

## 9. Risks & Limitations (reviewer should challenge)

1. **RSS-only sources**: v1 relies on RSS; official blogs without RSS need the scraper stub + external actor later.
2. **Hot score too simple**: `priority_weight x exponential time decay`, no real social signals; LLM bonus off by default.
3. **Embedding/semantic search**: `q` is ILIKE full-text fallback for now; pgvector semantic search interface stubbed but not wired.
4. **Clustering computes cosine in Python** (fine for small windows); at scale must move to pgvector ANN query.
5. **No rate limiting**: recommended before going public (Zeabur layer or FastAPI middleware).
6. **Cost**: Zeabur 5 services consume usage; Moonshot API is per-token (translation + insights are the main spend).

---

## 10. Suggested Review Path

1. Read repo `docs/01-product-overview.md` + sections 2/4 of this doc — confirm the premise "why an MCP server"
2. Compare `docs/04-mcp-server-spec.md` with `mcp-server/tools.py` — are the tools well-designed for agents
3. Compare `infra/ZEABUR-SETUP.md` with section 6 — any gaps in deployment topology
4. Answer the decision checklist in section 8 item by item
5. Challenge the risks in section 9, propose v1.1 priorities
