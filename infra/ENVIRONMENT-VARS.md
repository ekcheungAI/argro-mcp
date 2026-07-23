# Environment Variables Reference

Sources of truth, scanned from code:

- Backend / worker: `backend/app/config.py` (pydantic-settings `Settings`)
- MCP server: `mcp-server/client.py` (`BackendSettings`), `mcp-server/main.py` (`os.environ`)
- Frontend: `frontend/lib/apiClient.ts`, `frontend/README.md`
- Spec: `docs/07-infra-zeabur-plan.md` §2

"Required?" = the service fails or is meaningfully broken without it. Vars with
code defaults are technically optional but listed with their defaults.

## Backend & Worker (same image, same env)

Both `backend` (API) and `worker` (`python -m app.worker`) read the same
`Settings` object, so they share all of these.

| Variable | Used by | Required? | Default (in code) | Example | Notes |
| --- | --- | --- | --- | --- | --- |
| `DATABASE_URL` | backend, worker, migrate | **Yes** (prod) | `postgresql+psycopg://postgres:postgres@localhost:5432/argro` | `postgresql+psycopg://user:pass@host:5432/argro` | SQLAlchemy URL. **Must use the `postgresql+psycopg://` scheme** (psycopg 3 driver). On Zeabur, reference the Postgres service's connection-string variable and fix the scheme (see ZEABUR-SETUP.md FAQ). Also read by Alembic (`alembic/env.py`). |
| `APP_ENV` | backend, worker | No | `dev` | `prod` | `dev` \| `prod` (07 §2). |
| `BACKEND_PORT` | backend | No | `8000` | `8000` | Informational; the container CMD binds uvicorn to 8000 regardless. |
| `API_KEY` | backend, **mcp-server** | No | _(unset = auth off)_ | `change-me-shared-secret` | When set on the backend, API requests need the key; the MCP server sends it as the `X-API-Key` header. **Use the same value on both services.** |
| `MOONSHOT_API_KEY` | backend, worker | **Yes** for enrichment/translation/embeddings | _(unset)_ | `sk-...` | Moonshot (Kimi) API key. Without it, LLM-powered enrichment cannot run. |
| `MOONSHOT_BASE_URL` | backend, worker | No | `https://api.moonshot.ai/v1` | `https://api.moonshot.ai/v1` | Override only for proxies/compatible endpoints. |
| `EMBEDDING_MODEL` | backend, worker | No | `text-embedding-3-small` | `text-embedding-3-small` | Embedding model name (placeholder default in code). |
| `TRANSLATION_MODEL` | backend, worker | No | `kimi-k2` | `kimi-k2` | Chat model used for translation/summarisation. |
| `EMBEDDING_DIM` | backend, worker | No | `1536` | `1536` | Vector dimension; must match the DB column (`article_embeddings`). Change only together with a migration. |
| `TARGET_LANGS` | backend, worker | No | `en,zh-TW` | `en,zh-TW` | Comma-separated output languages. |
| `INGESTION_BATCH_SIZE` | worker | No | `50` | `50` | Items per ingestion batch (07 §2 backend-specific). |
| `INGESTION_INTERVAL_MINUTES` | worker | No | `15` | `15` | Interval between ingestion runs (07 §2). |
| `WORKER_CONCURRENCY` | worker | No | `4` | `4` | Parallel ingestion/enrichment tasks (07 §2 worker-specific). |
| `CORS_ORIGINS` | backend | No | _(not yet read by code)_ | `https://app.example.zeabur.app` | Reserved for the backend CORS middleware (allow-list of frontend origins). Currently not in `config.py`; set it once CORS middleware lands. See ZEABUR-SETUP.md FAQ. |

> 07 §2 also mentions `VECTOR_DB_URL` and `NEWS_API_KEY`: this project uses
> **pgvector inside the same Postgres**, so `DATABASE_URL` covers both (no
> separate `VECTOR_DB_URL`); ingestion uses RSS feeds (`app/seed.py`), so there
> is no `NEWS_API_KEY` in code. `CRON_EXPRESSION_INGESTION` is not implemented —
> scheduling is internal via `INGESTION_INTERVAL_MINUTES`.

## MCP server (`mcp-server/`)

| Variable | Used by | Required? | Default (in code) | Example | Notes |
| --- | --- | --- | --- | --- | --- |
| `MCP_BACKEND_URL` | mcp-server | **Yes** (prod) | `http://localhost:8000` | `https://api.example.zeabur.app` | Base URL of the backend HTTP API (07 §2). The server is stateless and never touches the DB. |
| `API_KEY` | mcp-server | No | _(unset)_ | `change-me-shared-secret` | Forwarded to the backend as `X-API-Key`. Must match the backend's `API_KEY` if backend auth is on. |
| `MCP_SERVER_HOST` | mcp-server | No | `0.0.0.0` | `0.0.0.0` | Bind host. Keep `0.0.0.0` in containers. |
| `MCP_SERVER_PORT` | mcp-server | No | `8100` | `8100` | Bind port; endpoint path is `/mcp` (streamable HTTP). |

## Frontend (`frontend/`)

| Variable | Used by | Required? | Default (in code) | Example | Notes |
| --- | --- | --- | --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | frontend | **Yes** (prod) | `http://localhost:8000` | `https://api.example.zeabur.app` | Backend base URL. **Build-time** (inlined by Next.js) AND runtime (React Server Components read `process.env` on the server) — set it as a Docker build arg and as a runtime env. If the backend ever mounts under a path prefix, include it (e.g. `https://api.example.com/v1`); endpoint paths are appended directly. |

## Local Postgres container (compose only)

| Variable | Used by | Required? | Default | Example | Notes |
| --- | --- | --- | --- | --- | --- |
| `POSTGRES_USER` | postgres | No | `postgres` | `postgres` | Also interpolated into the compose `DATABASE_URL`. |
| `POSTGRES_PASSWORD` | postgres | **Yes** (no default in image) | `postgres` (compose default) | `postgres` | Change for anything beyond a laptop. |
| `POSTGRES_DB` | postgres | No | `argro` | `argro` | Database created on first boot. |
