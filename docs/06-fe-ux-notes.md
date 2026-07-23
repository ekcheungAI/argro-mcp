# Frontend UX Notes

The frontend is a Next.js + React app consuming the HTTP API from 03-HTTP-API-SPEC.md.

## 1. Pages

1. **Home / Today**
   - Show:
     - Today’s hot AI news (from `/news/hot`).
     - Tabs or filters for topics (model releases, product updates, etc.).
   - Optional mini “Daily Insight” highlight.

2. **All News**
   - List with filters:
     - Time range (last 24h, 7 days, custom).
     - Topic filter.
     - Source filter.
     - Language filter.
     - Search box (maps to `q`).
   - Infinite scroll or pagination.

3. **Daily Insight**
   - For each date:
     - Show title, summary, and sections from `/insights/daily`.
   - Date picker for selecting past dates.

4. **Developers / Agents**
   - Show:
     - HTTP API docs (basic usage and examples).
     - MCP server connection info and example config.
     - Example prompts for agents.

## 2. Components / Layout

- **NewsCard**
  - Props: `title`, `summary`, `sourceName`, `publishedAt`, `topics`, `lang`, `originalLang`, `url`.
  - Show a badge for language if different from user’s selected language.

- **TopicFilter**
  - Multi-select topics.

- **LangSwitch**
  - Switch between `en` / `zh-TW` etc. with SSR-friendly routing or query param.

## 3. Visual Style

- Clean, information-dense layout (news/data first).
- Dark mode support preferred.
- Mobile-friendly list layout, desktop with side filters.

## 4. URL Structure (example)

- `/` – today hot news.
- `/all` – full stream.
- `/insights` – latest insight.
- `/insights/[date]` – specific date.
- `/developers` – API & MCP docs.
