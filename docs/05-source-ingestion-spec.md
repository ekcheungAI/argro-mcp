# Source Ingestion & Enrichment Specification

This document describes how we ingest, normalize, and enrich news data.

## 1. Source Types

- RSS: Most AI/tech media and official blogs expose RSS/Atom feeds.
- API: Some partners may expose JSON APIs.
- Scraper: For sites without RSS, we may call external actors (e.g. news aggregators) and normalize results.

## 2. Ingestion Flow

1. Periodically query `sources` table:
   - `is_active = true`.
2. For each source:
   - If `type = rss`: fetch `feed_url`, parse items.
   - If `type = api`: call the API, map fields.
   - If `type = scraper`: call external actor/API, map fields.
3. Convert each raw item to a normalized in-memory structure:

```ts
type RawArticle = {
  source_id: string;
  external_id?: string;
  url: string;
  title: string;
  summary?: string;
  content?: string;
  published_at: string; // ISO
  metadata?: Record<string, any>;
};
```

4. Deduplication:
   - Prefer unique (`source_id`, `external_id`) when available.
   - Fallback on (`source_id`, `url`).
5. Insert or update record in `articles`:
   - Set `fetched_at = now()`.
   - Keep original language if known from the feed; otherwise detect later.

## 3. Language Detection & Translation

- After insertion, run an enrichment job:
  1. Language detection:
     - Detect `original_lang` if not already known.
  2. Translations:
     - For target languages, e.g. `en` and `zh-TW`, call LLM/MT to produce:
       - `title`, `summary` (and optionally `content`).
     - Store into `article_translations` with `translation_model` metadata.

## 4. Topic Classification

- For each article (or translation), run topic classification:
  - Map to predefined topic keys: `model_release`, `product_update`, `industry_event`, `policy`, `research_paper`, `opinion_tutorial`.
  - Store in `article_topics` with a `confidence` score.
  - Maintain `topics_cached` as a text[] of top topics for fast filtering.

## 5. Embedding & Similarity

- Generate embedding for each article (preferably on cleaned `title + summary + content`).
- Write into `article_embeddings`.
- Use this for:
  - Semantic search.
  - Clustering into events: assign `cluster_id` to related articles.

## 6. Hot Score Calculation

- Compute `hot_score` based on:
  - `source.priority_weight`.
  - Recency (time decay).
  - Optional social signals if available (e.g. shares, upvotes).
  - LLM-based “information value” score.

This scoring job can run:
- Incrementally on new articles.
- Periodically re-scoring recent articles.

## 7. Scheduling

- Use a scheduler (cron/worker) to:
  - Ingestion: e.g. every 5–10 minutes for key sources, every 15–30 minutes for others.
  - Enrichment: batch process new articles.
  - Insights: generate daily/weekly summaries.
