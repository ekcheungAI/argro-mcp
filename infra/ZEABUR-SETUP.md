# Zeabur Deployment Guide (step by step)

Deploys all five components of `docs/07-infra-zeabur-plan.md` on Zeabur:
PostgreSQL+pgvector, backend, worker, mcp-server, frontend. Assumes nothing
exists yet — you only need a Zeabur account and this GitHub repo.

All Dockerfiles live in `infra/` and use the **repository root** as the Docker
build context. Keep that in mind for every service below.

---

## Step 1 — Create the project

1. Zeabur dashboard → **Create Project** → pick a region close to your users.
2. Name it e.g. `argro-mcp`.

You will add five services inside this project.

## Step 2 — Add PostgreSQL (+ pgvector)

1. In the project → **Add Service** → **Marketplace** → **PostgreSQL**.
2. Deploy it. Zeabur creates user/password/database and exposes variables such
   as `POSTGRES_CONNECTION_STRING`, `POSTGRESQL_CONNECTION_STRING`,
   `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USERNAME`, `POSTGRES_PASSWORD`,
   `POSTGRES_DATABASE` (names vary slightly by template version — check the
   service's **Variables** tab).

**pgvector** — two options; option A is the normal path:

- **A. Let the migration enable it (default).** The first Alembic migration
  (`backend/alembic/versions/0001_initial.py`) already runs
  `CREATE EXTENSION IF NOT EXISTS vector;`. The marketplace PostgreSQL image is
  pgvector-capable on current Zeabur templates, so Step 4 enables it
  automatically.
- **B. Enable it manually first** (if option A errors, or your template's image
  differs): open the Postgres service → **Console/Exec** (or connect with any
  psql client using the public host/port) and run:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```
  If you get `extension "vector" is not available`, the image lacks pgvector —
  switch to an external pgvector-capable DB (e.g. Supabase) and point
  `DATABASE_URL` at it instead.

## Step 3 — Add the backend service

1. **Add Service** → **GitHub** → select this repo. Zeabur creates one service
   per repo; rename it to `backend` (you'll add the same repo again for the
   worker — Zeabur lets you deploy multiple services from one repo).
2. **Use our Dockerfile**: in the service → **Settings** → set the build type
   to **Dockerfile** and the **Dockerfile path** to
   `infra/Dockerfile.backend` with **build context = repository root** (the
   default; the Dockerfile does `COPY backend/ /app/`). Do NOT set the root
   directory to `backend/` — the Dockerfile paths are relative to the repo
   root.
3. **Variables** tab — set (see `infra/ENVIRONMENT-VARS.md` for the full list):
   - `DATABASE_URL` — reference the Postgres service. In Zeabur you can
     reference another service's variables, e.g.
     `postgresql+psycopg://${POSTGRES_USERNAME}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DATABASE}`
     (substitute the actual variable names from Step 2; see FAQ about the
     `postgresql+psycopg://` scheme).
   - `MOONSHOT_API_KEY` — your Moonshot/Kimi key.
   - `APP_ENV=prod`.
   - `API_KEY` — optional shared secret (recommended; must match mcp-server).
   - Optional tuning: `INGESTION_BATCH_SIZE`, `INGESTION_INTERVAL_MINUTES`,
     `WORKER_CONCURRENCY`, `TARGET_LANGS`, `TRANSLATION_MODEL`,
     `EMBEDDING_MODEL`.
4. **Port / healthcheck**: the container listens on **8000**; configure the
   service port accordingly and set the healthcheck path to **`/healthz`**.
5. **Networking** tab → bind a domain (e.g. `api-yourapp.zeabur.app`). This is
   the public base URL used by the frontend and (optionally) the MCP server.

## Step 4 — Run migrations + seed (one-shot)

The schema (incl. `CREATE EXTENSION vector`, tables, HNSW index) and seed data
(topics + RSS sources) are applied by:

```bash
python -m alembic upgrade head && python -m app.seed
```

Run it **once** before/alongside the first backend boot — either:

- **A. Backend service console** (simplest): backend service → **Console/Exec**
  → run the command above. Safe to re-run (alembic tracks revisions; the seed
  is idempotent).
- **B. Temporary one-shot service**: add the repo again with the same
  `infra/Dockerfile.backend` and the same env, set the start command override
  to the command above, let it run once, then delete/pause the service.

> Locally this is automated by the `migrate` service in
> `infra/docker-compose.example.yml`; Zeabur has no compose `depends_on`, so we
> do it manually.

## Step 5 — Add the worker service

1. **Add Service** → **GitHub** → same repo again → rename to `worker`.
2. Same Dockerfile settings: `infra/Dockerfile.backend`, repo-root context.
3. **Start command override**: `python -m app.worker`
   (same image as the backend; only the entrypoint differs — 07 §1.2).
4. **Variables**: copy the backend's env (`DATABASE_URL`, `MOONSHOT_API_KEY`,
   `APP_ENV`, ingestion tuning…). Identical values — see Step 8 for sharing.
5. **No port, no domain** — the worker is internal-only. No healthcheck
   endpoint either (it exposes none); rely on restart policy.

## Step 6 — Add the mcp-server service

1. **Add Service** → **GitHub** → same repo → rename to `mcp-server`.
2. Dockerfile path: `infra/Dockerfile.mcp`, repo-root context.
3. Variables:
   - `MCP_BACKEND_URL` — the backend URL. Prefer Zeabur's **internal
     networking** address (the backend service's internal hostname, e.g.
     `http://backend.zeabur.internal:8000` — see the backend service's
     Networking tab) to keep traffic in-cluster; the public domain from Step 3
     also works.
   - `API_KEY` — same value as the backend's (if set).
   - `MCP_SERVER_PORT=8100` (default), `MCP_SERVER_HOST=0.0.0.0` (default).
4. Port **8100**; bind a domain (e.g. `mcp-yourapp.zeabur.app`). MCP clients
   connect to `https://mcp-yourapp.zeabur.app/mcp` (streamable HTTP).

## Step 7 — Add the frontend service

1. **Add Service** → **GitHub** → same repo → rename to `frontend`.
2. Dockerfile path: `infra/Dockerfile.frontend`, repo-root context.
3. **`NEXT_PUBLIC_API_BASE_URL` is a build-time variable**: set it to the
   backend's public domain (e.g. `https://api-yourapp.zeabur.app`) in the
   service **Variables** BEFORE the first build — the Dockerfile declares it as
   `ARG` and Zeabur passes service variables as build args; it is also kept as
   a runtime env for React Server Components. If you change it later,
   **redeploy/rebuild** the frontend.
4. Port **3000**; bind the user-facing domain (e.g. `yourapp.zeabur.app`).

## Step 8 — Shared env & scaling

- **Shared variables**: Zeabur supports project-level/shared variable
  references — define common values once (`DATABASE_URL`, `API_KEY`,
  `MOONSHOT_API_KEY`) and reference them from backend and worker so they can't
  drift. Otherwise copy-paste carefully.
- **Scaling** (service → Settings):
  - `backend`: 1–2 replicas. With >1 replica, always run migrations via Step 4
    (never in a startup script) to avoid races.
  - `worker`: exactly **1** replica (ingestion is interval-scheduled; running
    multiple workers duplicates fetches).
  - `mcp-server`: 1+ replicas; it is stateless (`stateless_http=True`), safe to
    scale.
  - `frontend`: 1–2 replicas.
- **Healthchecks**: backend `/healthz` on port 8000. mcp-server/frontend have
  no dedicated health endpoint — Zeabur's default TCP/HTTP root check is fine.

---

## Troubleshooting / FAQ

**`CORS` errors in the browser**
The frontend calls the backend cross-origin. If/when the backend enables CORS
middleware, set `CORS_ORIGINS` on the backend to the frontend's public domain
(e.g. `https://yourapp.zeabur.app`). If requests are proxied same-origin this
is unnecessary. (`CORS_ORIGINS` is reserved but not yet read by
`backend/app/config.py` — check the backend changelog.)

**`connection refused` / driver errors for `DATABASE_URL`**
The URL **must** use SQLAlchemy's psycopg-3 scheme:
`postgresql+psycopg://user:pass@host:5432/dbname`. Zeabur's ready-made
connection string is usually `postgresql://...` — add the `+psycopg` driver
suffix. Also `postgres://` (Heroku-style) is NOT accepted.

**`extension "vector" is not available` / pgvector errors during migration**
The Postgres image has no pgvector. Either use a pgvector-capable template
image, run Step 2 option B with `CREATE EXTENSION IF NOT EXISTS vector;` on a
capable DB, or switch to an external DB (Supabase etc.) and update
`DATABASE_URL`. Locally, `pgvector/pgvector:pg16` (compose) always works.

**`relation "topics" does not exist` on first boot**
Migrations haven't run — do Step 4 (`alembic upgrade head && app.seed`).

**Moonshot errors (`401` / enrichment not running)**
`MOONSHOT_API_KEY` missing or wrong on backend **and** worker. Embeddings,
translation and insight generation all need it.

**MCP client can't connect**
Endpoint is `https://<mcp-domain>/mcp` (streamable HTTP, POST). Check
`MCP_BACKEND_URL` points at the backend and `API_KEY` matches. Verify the
backend directly: `curl https://<api-domain>/healthz`.

**Frontend shows "Backend unavailable"**
`NEXT_PUBLIC_API_BASE_URL` is wrong or was changed without a rebuild — fix the
variable and redeploy the frontend (it is baked in at build time). Also check
the backend healthcheck and CORS.
