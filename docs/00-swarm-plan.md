# argro-mcp — Swarm Decomposition Plan

> Stage 1 deliverable. Waiting for user confirmation before any code is written.

## 0. Repo Scan Findings

- Repo `ekcheungAI/argro-mcp` is **completely empty** (no commits, no files).
- No existing MCP/code base to preserve → greenfield implementation.
- Directory structure will follow the brief: `docs/ backend/ mcp-server/ frontend/ infra/`.
- The 7 spec files (01–07) will be committed into `docs/` as the authoritative specs.

## 1. Locked Technical Decisions (from specs, no deviation)

| Area | Decision | Source |
|---|---|---|
| Backend | Python + FastAPI + SQLAlchemy + Alembic | Brief §技術選擇 |
| DB | PostgreSQL + pgvector | 02-DATA-MODEL |
| API | REST, exact endpoints + JSON shapes from 03 | 03-HTTP-API-SPEC |
| MCP server | Stateless, streamable-HTTP transport, calls backend over HTTP only (never DB direct) | 04-MCP-SERVER-SPEC |
| MCP tools | `get_daily_hot`, `search_news`, `get_article_detail`, `get_insight` (`get_trends` deferred — spec marks optional) | 04 |
| Frontend | Next.js (App Router) + React + TypeScript + Tailwind; pages `/`, `/all`, `/insights`, `/insights/[date]`, `/developers` | 06-FE-UX-NOTES |
| Deploy | Zeabur, 5 services: backend / worker / mcp-server / frontend / postgres(+pgvector) | 07-INFRA-ZEABUR-PLAN |

### Spec clarifications I will apply (flagging per brief, not silent changes)
1. **`articles.metadata` column**: `metadata` is a reserved attribute name in SQLAlchemy Declarative. ORM attribute will be `meta` mapped to DB column `metadata` — DB schema stays exactly per 02, only the Python attribute differs.
2. **Embedding dimension**: 02 says "e.g. 1536". I'll make dimension env-configurable (`EMBEDDING_DIM`, default 1536) with pgvector column sized at migration time.
3. **Auth**: 03 says public read-only MAY be open in early stages → `X-API-Key` middleware implemented but **off by default** via env flag.
4. **`topics_cached`** maintained by enrichment (top-N topic keys), per 05 §4.

## 2. Sub-Agents & Responsibilities

### Agent A — DB / ORM / Migrations
**Mission:** Everything data-layer, exactly per 02-DATA-MODEL.md.
- `backend/pyproject.toml` (shared with B — A creates, B extends if needed)
- `backend/app/config.py`, `backend/app/db.py`
- `backend/app/models/` — `source.py`, `article.py`, `article_translation.py`, `topic.py`, `article_topic.py`, `article_embedding.py`, `daily_insight.py`
- `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_initial.py` (all tables, constraints, indexes incl. GIN on `topics_cached`, pgvector index)
- `backend/app/seed.py` — seed default topics (6 keys from 02) + sample sources
**Gate:** migration SQL reviewed against every table/constraint/index in 02.

### Agent B — Backend HTTP API
**Mission:** FastAPI app + routers, exactly per 03-HTTP-API-SPEC.md.
- `backend/app/main.py` (app factory, `/healthz`)
- `backend/app/schemas/` — Pydantic v2 response models matching 03 JSON byte-for-byte (field names, nullability)
- `backend/app/routers/news.py` — `GET /news/stream` (filters, cursor pagination, `sort=time_desc|hot_desc`, lang fallback via translations), `GET /news/hot`, `GET /news/{id}` (incl. `cluster_related`)
- `backend/app/routers/insights.py` — `GET /insights/daily` (type/date/lang, latest fallback)
- `backend/app/routers/meta.py` — `GET /meta/sources`, `GET /meta/topics`
- `backend/app/deps.py` — pagination cursor helpers, lang-resolution helper, optional API-key dependency
- `backend/tests/test_api_contract.py` — contract tests asserting response shapes match 03 examples
**Depends on:** Agent A models.

### Agent C — Ingestion & Enrichment Worker
**Mission:** Pipeline per 05-SOURCE-INGESTION-SPEC.md.
- `backend/app/ingestion/base.py` — `RawArticle` dataclass (fields exactly per 05 §3)
- `backend/app/ingestion/rss.py` — feedparser-based RSS fetcher
- `backend/app/ingestion/api_source.py`, `scraper_source.py` — pluggable stubs with `meta` jsonb config
- `backend/app/ingestion/dedupe.py` — (source_id, external_id) → fallback (source_id, url)
- `backend/app/enrichment/lang_detect.py`, `translate.py`, `topics.py`, `embed.py`, `hot_score.py`, `cluster.py` — each behind a provider interface (LLM/MT/embedding endpoints via env; graceful no-op if keys absent)
- `backend/app/worker.py` — entrypoint `python -m app.worker`, internal scheduler (intervals per 05 §7, env-tunable)
- `backend/app/insights/generator.py` — daily/weekly insight generation into `daily_insights`
**Depends on:** Agent A models.

### Agent D — MCP Server
**Mission:** Stateless MCP server per 04-MCP-SERVER-SPEC.md.
- `mcp-server/pyproject.toml`
- `mcp-server/main.py` — FastMCP (official `mcp` Python SDK), streamable-HTTP transport, stateless
- `mcp-server/tools.py` — 4 tools with exact input schemas from 04; thin httpx wrappers → backend endpoints
- `mcp-server/README.md` — env config (`MCP_BACKEND_URL`, `MCP_SERVER_PORT`), client config examples (Claude/Cursor/Kimi)
**Depends on:** 03 spec only (HTTP contract) → can run in Wave 1, no dependency on A/B code.

### Agent E — Frontend (Next.js)
**Mission:** Web app per 06-FE-UX-NOTES.md.
- `frontend/` — Next.js App Router + TS + Tailwind scaffold
- `frontend/app/page.tsx` (Today hot + topic tabs + mini insight), `app/all/page.tsx` (filters + search + infinite scroll), `app/insights/page.tsx`, `app/insights/[date]/page.tsx`, `app/developers/page.tsx` (API + MCP docs, example prompts)
- `frontend/components/` — `NewsCard.tsx` (lang badge logic), `TopicFilter.tsx`, `LangSwitch.tsx`, `SourceFilter.tsx`, `SearchBox.tsx`
- `frontend/lib/apiClient.ts` — typed client for all 6 endpoints, base URL from `NEXT_PUBLIC_API_BASE_URL`
- Dark mode, mobile list / desktop side-filter layout per 06 §3
**Depends on:** 03 spec only (mockable) → can run in Wave 1.

### Agent F — Infra / Zeabur
**Mission:** Deployment artifacts per 07-INFRA-ZEABUR-PLAN.md.
- `infra/Dockerfile.backend`, `infra/Dockerfile.mcp`, `infra/Dockerfile.frontend` (worker reuses backend image, different CMD)
- `infra/docker-compose.example.yml` — backend, worker, mcp-server, frontend, postgres+pgvector
- `infra/ENVIRONMENT-VARS.md` — every env var from 07 §2 + new ones, with example values
- `infra/ZEABUR-SETUP.md` — concrete step-by-step: create project, add 5 services, Dockerfile paths, ports, env wiring (`DATABASE_URL`, `MCP_BACKEND_URL`, `NEXT_PUBLIC_API_BASE_URL`), healthcheck `/healthz`, scaling notes
**Depends on:** final Docker/start commands from A–E → runs last, but skeleton in Wave 2.

### Agent G — Review / Integration (verifier)
**Mission:** Final gate.
- Cross-check every file against specs 02/03/04/05/06/07 (endpoint names, JSON fields, table names — zero deviation)
- Boot the full stack via docker-compose, run contract tests, verify MCP tools list/call against live backend
- Produce `README.md` (root): local run guide + Zeabur deploy guide summary

## 3. Execution Order (3 waves)

```
Wave 1 (parallel):
  A: DB/ORM/migrations          ──┐
  D: MCP server (spec-only dep)   ├─ all independent
  E: Frontend (mock API client)  ─┘

Wave 2 (parallel, after A passes gate):
  B: Backend API (needs A models)
  C: Ingestion/Worker (needs A models)
  F: Infra skeleton (Dockerfiles)

Wave 3 (sequential):
  Integration: F finalizes compose/Zeabur docs with real commands
  G: Full review + docker-compose boot + contract tests + README
```

## 4. Final Deliverables Recap

- Full source for `backend/`, `mcp-server/`, `frontend/`, `infra/`, `docs/` (7 specs committed)
- Root `README.md` — local quickstart + Zeabur step-by-step
- Everything pushed to `github.com/ekcheungAI/argro-mcp` (needs your git auth when we get there)

## 5. Open Questions for You

1. **LLM/MT provider for translation + insights + embeddings** — Kimi (Moonshot) API? OpenAI? Worker is provider-agnostic via env, but default config should target one. (No keys needed from you now — I'll wire env placeholders.)
2. **Git push auth** — at implementation end I'll need a PAT or you push yourself. (Note: a git token you pasted in a previous session may be compromised since it appeared in chat — recommend revoking and issuing a fresh one.)
3. **Initial source list** — I'll seed ~10 well-known AI RSS feeds (OpenAI, Anthropic, DeepMind, TechCrunch AI, The Verge AI, arXiv cs.AI, etc.). OK, or do you have a preferred list?
