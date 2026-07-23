import Link from 'next/link';
import {
  ApiError,
  getHot,
  getInsight,
  getTopics,
  type InsightResponse,
  type NewsStreamResponse,
  type TopicItem,
} from '@/lib/apiClient';
import { normalizeParams, type RawSearchParams } from '@/lib/query';
import BackendUnavailable from '@/components/BackendUnavailable';
import EmptyState from '@/components/EmptyState';
import NewsCard from '@/components/NewsCard';

export const metadata = { title: 'Today' };

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<RawSearchParams>;
}) {
  const params = normalizeParams(await searchParams);
  const lang = params.lang;
  const topic = params.topic; // single-select on this page

  let hot: NewsStreamResponse;
  try {
    hot = await getHot({ lang, topic, limit: 30 });
  } catch {
    return <BackendUnavailable />;
  }

  // Secondary data must never break the page.
  const topics: TopicItem[] = await getTopics()
    .then((r) => r.topics)
    .catch(() => []);
  const insight: InsightResponse | null = await getInsight({ type: 'daily', lang }).catch(
    () => null,
  );

  const tabHref = (topicKey?: string) => {
    const qs = new URLSearchParams();
    if (topicKey) qs.set('topic', topicKey);
    if (lang) qs.set('lang', lang);
    const s = qs.toString();
    return s ? `/?${s}` : '/';
  };

  return (
    <div className="space-y-5">
      {insight && (
        <Link
          href="/insights"
          className="card block border-l-4 border-l-brand-600 p-4 transition-colors hover:border-brand-400"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600 dark:text-brand-400">
            Daily insight · {insight.date}
          </p>
          <p className="mt-1 font-medium leading-snug">{insight.title}</p>
          <p className="mt-1 line-clamp-2 text-sm text-neutral-600 dark:text-neutral-400">
            {insight.summary}
          </p>
        </Link>
      )}

      <div>
        <h1 className="text-lg font-bold">Today&apos;s hot AI news</h1>
        <div className="mt-3 flex flex-wrap gap-1.5" role="tablist" aria-label="Topics">
          <Link
            href={tabHref()}
            role="tab"
            aria-selected={!topic}
            className={`chip ${!topic ? 'chip-active' : ''}`}
          >
            All topics
          </Link>
          {topics.map((t) => (
            <Link
              key={t.key}
              href={tabHref(t.key)}
              role="tab"
              aria-selected={topic === t.key}
              title={t.description}
              className={`chip ${topic === t.key ? 'chip-active' : ''}`}
            >
              {t.name}
            </Link>
          ))}
        </div>
      </div>

      {hot.items.length === 0 ? (
        <EmptyState
          title="No hot news right now"
          description="There are no hot items for this selection yet. Try another topic or check the full stream."
          action={
            <Link href="/all" className="text-sm font-medium text-brand-700 hover:underline dark:text-brand-300">
              Browse all news →
            </Link>
          }
        />
      ) : (
        <div className="space-y-3">
          {hot.items.map((item) => (
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
              userLang={lang}
              hotScore={item.hot_score}
            />
          ))}
        </div>
      )}
    </div>
  );
}
