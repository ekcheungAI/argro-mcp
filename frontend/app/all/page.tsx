import {
  getSources,
  getStream,
  getTopics,
  type NewsStreamResponse,
  type SourceItem,
  type StreamParams,
  type TopicItem,
} from '@/lib/apiClient';
import { normalizeParams, type RawSearchParams } from '@/lib/query';
import BackendUnavailable from '@/components/BackendUnavailable';
import EmptyState from '@/components/EmptyState';
import LoadMore from '@/components/LoadMore';
import NewsCard from '@/components/NewsCard';
import SearchBox from '@/components/SearchBox';
import SourceFilter from '@/components/SourceFilter';
import TimeRangeFilter from '@/components/TimeRangeFilter';
import TopicFilter from '@/components/TopicFilter';

export const metadata = { title: 'All News' };

const PAGE_SIZE = 30;

function resolveTimeRange(params: Record<string, string>): { from?: string; to?: string } {
  const range = params.range ?? '24h';
  const now = Date.now();
  if (range === '7d') return { from: new Date(now - 7 * 24 * 3600_000).toISOString() };
  if (range === 'custom') return { from: params.from, to: params.to };
  return { from: new Date(now - 24 * 3600_000).toISOString() };
}

export default async function AllNewsPage({
  searchParams,
}: {
  searchParams: Promise<RawSearchParams>;
}) {
  const params = normalizeParams(await searchParams);
  const { from, to } = resolveTimeRange(params);

  const streamParams: StreamParams = {
    from,
    to,
    lang: params.lang,
    topic: params.topic,
    source: params.source,
    q: params.q,
    sort: 'time_desc',
    limit: PAGE_SIZE,
  };

  let data: NewsStreamResponse;
  try {
    data = await getStream(streamParams);
  } catch {
    return <BackendUnavailable />;
  }

  // Filter metadata must never break the page.
  const topics: TopicItem[] = await getTopics()
    .then((r) => r.topics)
    .catch(() => []);
  const sources: SourceItem[] = await getSources()
    .then((r) => r.sources)
    .catch(() => []);

  return (
    <div className="grid gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
      <aside className="space-y-5 lg:sticky lg:top-20 lg:self-start">
        <section>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Time range
          </h2>
          <TimeRangeFilter params={params} basePath="/all" />
        </section>
        <section>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Topics
          </h2>
          <TopicFilter topics={topics} params={params} basePath="/all" />
        </section>
        <section>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Sources
          </h2>
          <SourceFilter sources={sources} params={params} basePath="/all" />
        </section>
        <p className="text-xs text-neutral-400">
          Language is switched globally via the EN / 繁中 toggle in the top bar.
        </p>
      </aside>

      <section className="space-y-4">
        <SearchBox value={params.q} params={params} basePath="/all" />
        <p className="text-xs text-neutral-500 dark:text-neutral-500">
          {data.items.length} item{data.items.length === 1 ? '' : 's'}
          {params.q && (
            <>
              {' '}
              for “<span className="font-medium">{params.q}</span>”
            </>
          )}
        </p>
        {data.items.length === 0 ? (
          <EmptyState
            title="No news matches these filters"
            description="Try widening the time range, clearing the search, or removing some filters."
          />
        ) : (
          <div className="space-y-3">
            {data.items.map((item) => (
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
                userLang={params.lang}
              />
            ))}
            <LoadMore
              initialCursor={data.next_cursor}
              params={streamParams}
              userLang={params.lang}
            />
          </div>
        )}
      </section>
    </div>
  );
}
