import Link from 'next/link';
import type { TopicItem } from '@/lib/apiClient';
import { buildHref, toggleCsv } from '@/lib/query';

/**
 * Multi-select topic filter. Selection is stored in the `topic` query param
 * as a comma-separated list (matches the API contract). Rendered as plain
 * links, so it works without client-side JS.
 */
export default function TopicFilter({
  topics,
  params,
  basePath,
}: {
  topics: TopicItem[];
  /** Current normalized query params for the page. */
  params: Record<string, string>;
  basePath: string;
}) {
  const selected = new Set((params.topic ?? '').split(',').filter(Boolean));

  if (topics.length === 0) {
    return (
      <p className="text-xs text-neutral-500 dark:text-neutral-500">
        Topic list unavailable.
      </p>
    );
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {topics.map((topic) => {
        const active = selected.has(topic.key);
        const next = toggleCsv(params.topic, topic.key);
        return (
          <Link
            key={topic.key}
            href={buildHref(basePath, params, { topic: next, cursor: undefined })}
            title={topic.description}
            aria-pressed={active}
            className={`chip ${active ? 'chip-active' : ''}`}
          >
            {topic.name}
          </Link>
        );
      })}
    </div>
  );
}
