# AI News Platform – Product Overview

## 1. Product Positioning

We are building a multi-source, multi-language AI news aggregation and insight platform.

Goals:
- Aggregate AI-related news from multiple sources (official blogs, tech media, research, social).
- Normalize, enrich (language detection, translation, topic classification, clustering, scoring).
- Expose the data via:
  - Web app (daily brief, hot list, full stream).
  - HTTP API for internal use and partners.
  - MCP server tools so AI agents (Claude, Kimi, Cursor, etc.) can query “latest AI activity”.

Long-term vision:
- Become an AI-domain “news/data infra layer” that other agents and products rely on.

## 2. Target Users

- Builders / founders / PMs who need a fast overview of latest AI updates.
- Researchers / content creators tracking model and product releases.
- AI agents via MCP, consuming structured AI news data for downstream tasks.

## 3. Key Use Cases

1. “What happened in AI today?”
   - User or agent asks for a daily summary / hot list.
2. “Show me all recent updates about a specific model/vendor/topic.”
   - Filtered news stream, with search & topics.
3. “Give me a weekly AI industry brief.”
   - Precomputed insights and time-based aggregation.

## 4. High-Level Architecture

Layers:
- Source layer: RSS, APIs, scrapers, social feeds.
- Ingestion & normalization layer: fetch, dedupe, basic cleaning to a unified schema.
- Enrichment layer: language detection, translation, topic classification, clustering, embedding.
- Storage & query layer: PostgreSQL + vector search (pgvector or external).
- Delivery layer:
  - HTTP API (REST).
  - MCP server tools wrapping the API.
  - Web frontend.

## 5. Non-Goals (for v1)

- No user login or personalization in v1.
- No complex analytics dashboards for end users (basic insights only).
- No write APIs (everything is read-only for consumers).

## 6. Tech Preferences

- Backend: Python (FastAPI) or TypeScript (NestJS) – choose one and keep it standard.
- DB: PostgreSQL (+ pgvector for semantic search).
- MCP server: follow official MCP best practices, stateless HTTP-based server.
- Frontend: Next.js + React.
