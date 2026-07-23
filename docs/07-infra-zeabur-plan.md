# Infra & Deployment – Zeabur Plan

We want to deploy the whole system on Zeabur:

- Backend API service.
- Ingestion worker (scraper/enrichment).
- MCP server.
- Frontend (Next.js).
- PostgreSQL + pgvector (managed DB if available, or self-hosted as a service).

## 1. Services Overview

1. **backend**
   - Tech: FastAPI / NestJS.
   - Responsibilities:
     - Implement HTTP API (`/news/*`, `/insights/*`, `/meta/*`).
     - ORM migrations and DB access.
   - Ports: `8000` (internal), expose via Zeabur HTTP.

2. **worker**
   - Tech: same stack as backend, separated process.
   - Responsibilities:
     - Run ingestion + enrichment scheduled jobs.
     - Can be a separate entrypoint (e.g. `python -m app.worker`).
   - Trigger:
     - Use Zeabur’s cron/scheduler if available, or long-running worker with internal scheduling.

3. **mcp-server**
   - Tech: Python or Node MCP server.
   - Responsibilities:
     - Implement tools from 04-MCP-SERVER-SPEC.md.
     - Talk to backend via HTTP (NOT directly to DB, to keep stateless).
   - Ports: as required for MCP transport (HTTP/WS).
   - Expose: internal/external depending on MCP client requirements.

4. **frontend**
   - Tech: Next.js.
   - Responsibilities:
     - Web UI consuming backend API.
   - Deployment:
     - As Zeabur web app, configured to point to backend API base URL.

5. **database**
   - PostgreSQL with pgvector.
   - Provisioned either as:
     - Zeabur managed DB, or
     - External managed DB (Supabase/RDS/Cloud SQL) connected via env vars.

## 2. Environment Variables

Common:

- `DATABASE_URL` – PostgreSQL connection string.
- `VECTOR_DB_URL` or same as `DATABASE_URL` if using pgvector.
- `NEWS_API_KEY` or external actor tokens (if any).
- `MCP_BACKEND_URL` – base URL for backend (used by MCP server).
- `APP_ENV` – `dev` | `prod`.

Backend-specific:

- `BACKEND_PORT` – default 8000.
- `INGESTION_BATCH_SIZE`, `INGESTION_INTERVAL_MINUTES`.

Worker-specific:

- `WORKER_CONCURRENCY`.
- `CRON_EXPRESSION_INGESTION` (if using cron-like scheduler).

MCP-specific:

- `MCP_SERVER_PORT`.
- Any auth tokens if required.

Frontend-specific:

- `NEXT_PUBLIC_API_BASE_URL` – backend base URL.

## 3. Deployment Strategy on Zeabur

- Each of backend, worker, mcp-server, frontend is a separate Zeabur service pointing to its respective Dockerfile or build config.
- Use Zeabur environment groups or templates to share common env vars (DB, API base URL).
- Ensure backend has healthcheck endpoints (`/healthz`) for Zeabur to monitor.

## 4. Local Development vs Zeabur

- Local:
  - Use docker-compose with services:
    - `backend`, `worker`, `mcp-server`, `frontend`, `postgres`.
- Zeabur:
  - Mirror the same set of services, but connect to Zeabur-managed or external Postgres.
  - Use Zeabur dashboard to configure env vars and scaling.
