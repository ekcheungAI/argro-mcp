'use client';

import { useState } from 'react';
import { getStream, type NewsStreamItem, type StreamParams } from '@/lib/apiClient';
import NewsCard from './NewsCard';

/**
 * Cursor-based "Load more" for the /all stream. The first page is rendered
 * on the server; this component fetches subsequent pages directly from the
 * API using next_cursor and appends them.
 */
export default function LoadMore({
  initialCursor,
  params,
  userLang,
}: {
  initialCursor: string | null;
  /** Filter params of the current view (cursor excluded — managed here). */
  params: StreamParams;
  userLang?: string;
}) {
  const [items, setItems] = useState<NewsStreamItem[]>([]);
  const [cursor, setCursor] = useState<string | null>(initialCursor);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  if (initialCursor === null && items.length === 0) return null;

  const load = async () => {
    if (!cursor || loading) return;
    setLoading(true);
    setError(false);
    try {
      const res = await getStream({ ...params, cursor });
      setItems((prev) => [...prev, ...res.items]);
      setCursor(res.next_cursor);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {items.map((item) => (
        <NewsCard
          key={item.id}
          title={item.title}
          summary={item.summary}
          sourceName={item.source.name}
          publishedAt={item.published_at}
          topics={item.topics}
          lang={item.lang}
          originalLang={item.original_lang}
          url={item.url}
          userLang={userLang}
        />
      ))}
      {error && (
        <p className="py-2 text-center text-sm text-red-600 dark:text-red-400">
          Failed to load more.{' '}
          <button type="button" onClick={load} className="underline">
            Retry
          </button>
        </p>
      )}
      {cursor && (
        <div className="py-2 text-center">
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="rounded-md border border-neutral-300 px-4 py-2 text-sm font-medium transition-colors hover:border-brand-500 hover:text-brand-700 disabled:opacity-50 dark:border-neutral-700 dark:hover:text-brand-300"
          >
            {loading ? 'Loading…' : 'Load more'}
          </button>
        </div>
      )}
    </>
  );
}
