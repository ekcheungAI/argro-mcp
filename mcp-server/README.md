# ai-news-mcp-server

Multi-source AI news and insights for agents: hot list, search, and structured daily briefs.

A **stateless** MCP server (official Python `mcp` SDK, FastMCP, streamable-HTTP transport)
that exposes the AI news platform to AI assistants as MCP tools. It only talks to the
backend HTTP API (see `docs/03-http-api-spec.md`) — it never touches the database directly.

## Tools (docs/04-mcp-server-spec.md)

| Tool | Backend endpoint | Description |
| --- | --- | --- |
| `get_daily_hot(date?, lang?, limit=30)` | `GET /news/hot` | Hot AI news list for a specific date and language |
| `search_news(query*, lang?, from?, to?, topic?, limit=20)` | `GET /news/stream` (`q=query`) | Search AI news by natural language query and filters |
| `get_article_detail(id*, lang?)` | `GET /news/{id}` | Full detail for a selected article |
| `get_insight(type='daily' [daily\|weekly], date?, lang?)` | `GET /insights/daily` | Structured daily/weekly insight brief |

All tool responses are the backend JSON passed through unchanged.

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `MCP_BACKEND_URL` | `http://localhost:8000` | Base URL of the backend HTTP API |
| `API_KEY` | _(unset)_ | Optional API key; sent as `X-API-Key` header to the backend when set |
| `MCP_SERVER_HOST` | `0.0.0.0` | Bind host for the MCP server |
| `MCP_SERVER_PORT` | `8100` | Bind port for the MCP server |

## Run locally

```bash
cd mcp-server
pip install -e .
export MCP_BACKEND_URL=http://localhost:8000   # backend API
python main.py
```

The MCP endpoint is served at `http://localhost:8100/mcp` (streamable-HTTP, JSON responses).

## Client configuration

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ai-news": {
      "type": "http",
      "url": "http://localhost:8100/mcp"
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "ai-news": {
      "type": "streamable-http",
      "url": "http://localhost:8100/mcp"
    }
  }
}
```

### Kimi

In Kimi's MCP settings, add a streamable-HTTP server:

```json
{
  "mcpServers": {
    "ai-news": {
      "type": "streamable-http",
      "url": "http://localhost:8100/mcp"
    }
  }
}
```

Replace `localhost:8100` with the deployed URL for remote use.

## Deployment (Zeabur)

Deploy this directory as a Python service:

- **Build/install**: `pip install -e .`
- **Start command**: `python main.py`
- **Port**: the service listens on `MCP_SERVER_PORT` (default `8100`); expose this port
  (or set `MCP_SERVER_PORT` to the platform-assigned `PORT`).
- **Required env vars**:
  - `MCP_BACKEND_URL` — the public URL of the backend API service (e.g. `https://<backend>.zeabur.app`)
  - `API_KEY` — API key for the backend, if the backend enforces `X-API-Key` auth
- **Optional env vars**: `MCP_SERVER_HOST` (default `0.0.0.0`), `MCP_SERVER_PORT` (default `8100`)

After deployment, point clients at `https://<your-service>.zeabur.app/mcp`.
