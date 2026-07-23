/**
 * Typed client for the AIGRO HTTP API (see docs/03-http-api-spec.md).
 *
 * Base URL is configurable via NEXT_PUBLIC_API_BASE_URL. If the backend
 * mounts the API under a prefix (e.g. /v1), the env var must include it:
 *   NEXT_PUBLIC_API_BASE_URL=https://api.example.com/v1
 *
 * All functions throw ApiError on network failure or non-2xx responses —
 * callers (pages/components) must catch and render an appropriate state.
 */

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'
).replace(/\/+$/, '');

export class ApiError extends Error {
  readonly status?: number;
  readonly url: string;

  constructor(message: string, url: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.url = url;
    this.status = status;
  }
}

/* ------------------------------------------------------------------ */
/* Types (field-for-field from docs/03-http-api-spec.md)               */
/* ------------------------------------------------------------------ */

export interface SourceRef {
  id: string;
  name: string;
}

export interface NewsStreamItem {
  id: string;
  title: string;
  summary: string | null;
  url: string;
  /** Language of the returned fields (may be a translation). */
  lang: string;
  /** Language of the original article. */
  original_lang: string;
  /** ISO8601 datetime, e.g. "2026-07-23T08:00:00Z". */
  published_at: string;
  source: SourceRef;
  topics: string[];
  hot_score: number;
  cluster_id: string | null;
}

export interface NewsStreamResponse {
  items: NewsStreamItem[];
  next_cursor: string | null;
}

export interface ArticleTopic {
  key: string;
  name: string;
  confidence: number;
}

export interface ClusterRelatedItem {
  id: string;
  title: string;
  url: string;
  source: SourceRef;
}

export interface ArticleDetail {
  id: string;
  title: string;
  summary: string | null;
  content: string | null;
  url: string;
  lang: string;
  original_lang: string;
  published_at: string;
  source: SourceRef & { homepage_url: string };
  topics: ArticleTopic[];
  hot_score: number;
  cluster_id: string | null;
  cluster_related: ClusterRelatedItem[];
  metadata: Record<string, unknown>;
}

export interface InsightSection {
  section_title: string;
  content: string;
  /** Article ids, resolvable via GET /news/{id}. */
  articles: string[];
}

export interface InsightResponse {
  id: string;
  type: 'daily' | 'weekly';
  date: string; // YYYY-MM-DD
  lang: string;
  title: string;
  summary: string;
  sections: InsightSection[];
}

export interface SourceItem {
  id: string;
  name: string;
  type: string;
  lang: string;
  homepage_url: string;
  feed_url: string | null;
  priority_weight: number;
  is_active: boolean;
}

export interface SourcesResponse {
  sources: SourceItem[];
}

export interface TopicItem {
  key: string;
  name: string;
  description: string;
}

export interface TopicsResponse {
  topics: TopicItem[];
}

/* ------------------------------------------------------------------ */
/* Query param shapes (names must match 03 spec exactly)               */
/* ------------------------------------------------------------------ */

export type QueryParams = Record<string, string | number | undefined>;

export interface StreamParams {
  from?: string;
  to?: string;
  lang?: string;
  topic?: string;
  source?: string;
  q?: string;
  sort?: 'time_desc' | 'hot_desc';
  limit?: number;
  cursor?: string;
}

export interface HotParams {
  date?: string; // YYYY-MM-DD
  lang?: string;
  topic?: string;
  limit?: number;
}

export interface InsightParams {
  type?: 'daily' | 'weekly';
  date?: string; // YYYY-MM-DD
  lang?: string;
}

/* ------------------------------------------------------------------ */
/* Fetch helpers                                                       */
/* ------------------------------------------------------------------ */

function buildUrl(path: string, params?: QueryParams): string {
  const qs = new URLSearchParams();
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== '') qs.set(key, String(value));
    }
  }
  const query = qs.toString();
  return `${API_BASE_URL}${path}${query ? `?${query}` : ''}`;
}

async function request<T>(path: string, params?: QueryParams): Promise<T> {
  const url = buildUrl(path, params);
  let res: Response;
  try {
    res = await fetch(url, {
      cache: 'no-store',
      headers: { Accept: 'application/json' },
    });
  } catch (err) {
    throw new ApiError(
      `Backend unavailable: ${err instanceof Error ? err.message : String(err)}`,
      url,
    );
  }
  if (!res.ok) {
    throw new ApiError(`API error ${res.status} ${res.statusText}`, url, res.status);
  }
  return (await res.json()) as T;
}

/* ------------------------------------------------------------------ */
/* Endpoints                                                           */
/* ------------------------------------------------------------------ */

/** GET /news/stream */
export function getStream(params: StreamParams = {}): Promise<NewsStreamResponse> {
  return request<NewsStreamResponse>('/news/stream', {
    from: params.from,
    to: params.to,
    lang: params.lang,
    topic: params.topic,
    source: params.source,
    q: params.q,
    sort: params.sort,
    limit: params.limit,
    cursor: params.cursor,
  });
}

/** GET /news/hot */
export function getHot(params: HotParams = {}): Promise<NewsStreamResponse> {
  return request<NewsStreamResponse>('/news/hot', {
    date: params.date,
    lang: params.lang,
    topic: params.topic,
    limit: params.limit,
  });
}

/** GET /news/{id} */
export function getArticle(id: string, params: { lang?: string } = {}): Promise<ArticleDetail> {
  return request<ArticleDetail>(`/news/${encodeURIComponent(id)}`, {
    lang: params.lang,
  });
}

/** GET /insights/daily */
export function getInsight(params: InsightParams = {}): Promise<InsightResponse> {
  return request<InsightResponse>('/insights/daily', {
    type: params.type,
    date: params.date,
    lang: params.lang,
  });
}

/** GET /meta/sources */
export function getSources(): Promise<SourcesResponse> {
  return request<SourcesResponse>('/meta/sources');
}

/** GET /meta/topics */
export function getTopics(): Promise<TopicsResponse> {
  return request<TopicsResponse>('/meta/topics');
}
