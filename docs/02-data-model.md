# Data Model

This document defines the logical data model for the AI News Platform.

We will assume PostgreSQL as the primary database, with pgvector (or equivalent) for embeddings.

## 1. Entity Relationship Overview

Main entities:

- `sources`: where we get news from.
- `articles`: normalized news items (per URL/per original article).
- `article_translations`: translated versions of an article.
- `topics` + `article_topics`: taxonomy and per-article labels.
- `article_embeddings`: semantic embeddings for search and clustering.
- `daily_insights`: generated daily/weekly summaries.

## 2. Table Definitions

### 2.1 sources

Stores all news sources (RSS, APIs, scrapers, social).

- `id` (uuid / bigserial, PK)
- `name` (text) – display name, e.g. "TechCrunch AI"
- `type` (text enum: `rss`, `api`, `scraper`, `social`)
- `lang` (text, e.g. `en`, `zh-CN`, `zh-TW`, `ja`)
- `homepage_url` (text)
- `feed_url` (text, nullable; RSS/API endpoint etc.)
- `priority_weight` (float) – weight for hot scoring
- `is_active` (bool)
- `meta` (jsonb) – extra config (scraper selectors, auth info, etc.)
- `created_at` (timestamptz)
- `updated_at` (timestamptz)

Indexes:
- `idx_sources_active` on (`is_active`)
- `idx_sources_type` on (`type`)

### 2.2 articles

Normalized news items.

- `id` (uuid, PK)
- `source_id` (uuid, FK → sources.id)
- `external_id` (text, nullable; source-specific ID or guid for dedupe)
- `url` (text, NOT NULL)
- `original_lang` (text, NOT NULL)
- `title` (text, NOT NULL)
- `summary` (text, nullable)
- `content` (text, nullable) – cleaned text or simplified HTML
- `published_at` (timestamptz, NOT NULL)
- `fetched_at` (timestamptz, NOT NULL)
- `hot_score` (float, NOT NULL DEFAULT 0)
- `cluster_id` (uuid, nullable) – for event clustering
- `topics_cached` (text[] DEFAULT '{}') – main topic keys for quick filtering
- `metadata` (jsonb DEFAULT '{}') – author, tags, region, etc.
- `status` (text enum: `active`, `duplicate`, `blocked`)

Constraints / indexes:
- Unique (`source_id`, `external_id`) where `external_id` is not null.
- Unique (`source_id`, `url`).
- Index on (`published_at` DESC).
- Index on (`hot_score` DESC).
- GIN index on `topics_cached`.

### 2.3 article_translations

Per-language translations of articles.

- `id` (uuid, PK)
- `article_id` (uuid, FK → articles.id)
- `lang` (text, NOT NULL) – target language, e.g. `en`, `zh-TW`
- `title` (text, NOT NULL)
- `summary` (text, nullable)
- `content` (text, nullable)
- `translation_model` (text, nullable) – e.g. `"kimi-k2"`, `"gpt-4.1"`
- `created_at` (timestamptz, NOT NULL)

Unique:
- Unique (`article_id`, `lang`)

### 2.4 topics

Taxonomy of topics.

- `id` (serial, PK)
- `key` (text, unique, NOT NULL)
  - Examples: `model_release`, `product_update`, `industry_event`, `policy`, `research_paper`, `opinion_tutorial`
- `name` (text, NOT NULL)
- `description` (text, nullable)

### 2.5 article_topics

Mapping between articles and topics.

- `article_id` (uuid, FK → articles.id)
- `topic_id` (int, FK → topics.id)
- `confidence` (float, NOT NULL DEFAULT 0)

Primary key:
- (`article_id`, `topic_id`)

### 2.6 article_embeddings

Semantic embedding vectors for search and clustering.

- `article_id` (uuid, PK, FK → articles.id)
- `embedding` (vector) – e.g. 1536-dimension pgvector
- `model` (text, NOT NULL)
- `created_at` (timestamptz, NOT NULL)

Index:
- Vector index on `embedding`.

### 2.7 daily_insights

Generated daily/weekly insight documents.

- `id` (uuid, PK)
- `date` (date, NOT NULL)
- `lang` (text, NOT NULL)
- `type` (text enum: `daily`, `weekly`)
- `title` (text, NOT NULL)
- `summary` (text, NOT NULL)
- `sections` (jsonb, NOT NULL)
  - e.g. array of `{ "section_title": "...", "content": "...", "articles": ["article_id"...] }`
- `generated_from` (jsonb, NOT NULL)
  - includes model name, parameters, referenced article ids, etc.
- `created_at` (timestamptz, NOT NULL)

Unique:
- Unique (`type`, `date`, `lang`)
