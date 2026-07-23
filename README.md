# AIGRO — AI News Aggregation Platform + MCP Server

AIGRO is a multi-source AI news aggregation and insight platform. It ingests
AI news from RSS feeds / APIs / scrapers, normalizes and enriches them
(language detection, translation, topic classification, embeddings, hot
scoring, event clustering), and serves the result through a FastAPI HTTP API,
an MCP server for AI agents, and a Next.js web UI.

## Architecture

```
                     RSS / API / scraper sources
                                |
                                v
                     +----------------------+
                     |  worker (ingestion + |
                     |  enrichment jobs)    |
                     +----------+-----------+
                                |
                                v
                     +----------------------+
                     | PostgreSQL + pgvector|
                     +----------+-----------+
                                |
                                v
                     +----------------------+
                     | FastAPI backend      |
                     | /news /insights /meta|
                     +----+-------------+---+
                          |             |
              HTTP (stateless)          | HTTP
                          |             |
                +---------v--+   +------v-------+
                | MCP server |   | Next.js web  |
                | (4 tools)  |   | frontend     |
                +------------+   +--------------+
```

## Repository layout

```
backend/      FastAPI app, SQLAlchemy models, Alembic migrations,
              ingestion + enrichment pipeline, worker, seed script
mcp-server/   FastMCP server (stateless, streamable HTTP) proxying the backend
frontend/     Next.js 15 web UI
infra/        Dockerfiles, docker-compose.example.yml, env reference,
              Zeabur deployment guide
docs/         Authoritative specs (01 product → 07 infra)
```

## Quickstart (Docker Compose)

```bash
cp infra/.env.example infra/.env   # adjust values as needed
docker compose -f infra/docker-compose.example.yml --env-file infra/.env up --build
```

This starts: `postgres` (pgvector/pg16), a one-shot `migrate` service
(`alembic upgrade head` + seed), `backend` (:8000), `worker`,
`mcp-server` (:8100, path `/mcp`), and `frontend` (:3000).

## Quickstart (manual)

Requires Python 3.11+, Node 20+, and a PostgreSQL instance with the
`pgvector` extension available.

```bash
# 1. Backend deps
cd backend && pip install -e ".[dev]"

# 2. Point at your database (default: localhost postgres/argro)
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/argro

# 3. Schema + seed data (topics + RSS sources)
python -m alembic upgrade head
python -m app.seed

# 4. API server (http://localhost:8000, docs at /docs)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 5. Ingestion / enrichment worker (separate process)
python -m app.worker

# 6. MCP server (http://localhost:8100/mcp)
cd ../mcp-server && pip install -e . && python main.py

# 7. Frontend (http://localhost:3000)
cd ../frontend && npm ci && npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` for the frontend, and
`MCP_BACKEND_URL=http://localhost:8000` for the MCP server (both defaults).

## HTTP API (backend)

| Endpoint | Description |
| --- | --- |
| `GET /news/stream` | Paginated article stream (`from/to/lang/topic/source/q/sort/limit/cursor`) |
| `GET /news/hot` | Hottest articles for a date (`date/lang/topic/limit`) |
| `GET /news/{id}` | Article detail, topics, cluster-related articles |
| `GET /insights/daily` | Daily/weekly insight document (`type/date/lang`) |
| `GET /meta/sources` | Active sources |
| `GET /meta/topics` | Topic taxonomy |
| `GET /healthz` | Health check |

Optional auth: set `API_KEY` on the backend and send `X-API-Key: <key>`.

## MCP tools (`ai-news-mcp-server`)

| Tool | Maps to |
| --- | --- |
| `get_daily_hot` | `GET /news/hot` |
| `search_news` | `GET /news/stream` (`q=query` + filters) |
| `get_article_detail` | `GET /news/{id}` |
| `get_insight` | `GET /insights/daily` |

Transport: streamable HTTP at `http://localhost:8100/mcp`.

## Deployment (Zeabur)

See [`infra/ZEABUR-SETUP.md`](infra/ZEABUR-SETUP.md) for the full guide:
five services (postgres, backend, worker, mcp-server, frontend), one
Dockerfile each in `infra/`, healthcheck on `/healthz`.

## Environment variables

See [`infra/ENVIRONMENT-VARS.md`](infra/ENVIRONMENT-VARS.md) for the complete
reference (backend/worker, MCP server, frontend, compose Postgres).

## Tests

```bash
cd backend && PYTHONPATH=. python -m pytest tests/ -v
```
