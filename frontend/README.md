# AIGRO Frontend

Next.js (App Router) + TypeScript + Tailwind CSS frontend for AIGRO, the AI news
aggregation platform. Consumes the HTTP API defined in `docs/03-http-api-spec.md`.

## Setup

```bash
npm install
```

### Configuration

The API base URL is read from `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`):

```bash
# .env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

> **Important:** if the backend mounts the API under a path prefix, the env var
> must include it, e.g. `NEXT_PUBLIC_API_BASE_URL=https://api.example.com/v1`.
> Endpoint paths (`/news/hot`, `/news/stream`, …) are appended directly to this value.

## Develop

```bash
npm run dev      # http://localhost:3000
```

## Build / production

```bash
npm run build
npm start
```

## Lint / typecheck

```bash
npm run lint
npx tsc --noEmit
```

## Pages

| Route             | Data                                              |
| ----------------- | ------------------------------------------------- |
| `/`               | `GET /news/hot` + `GET /meta/topics` + mini `GET /insights/daily` |
| `/all`            | `GET /news/stream` (+ `/meta/topics`, `/meta/sources` for filters) |
| `/insights`       | `GET /insights/daily` (latest)                    |
| `/insights/[date]`| `GET /insights/daily?date=YYYY-MM-DD`             |
| `/developers`     | Static API & MCP docs                             |

All data fetching happens in React Server Components with `cache: 'no-store'`.
If the backend is unreachable, pages render a "Backend unavailable" empty state
instead of crashing.
