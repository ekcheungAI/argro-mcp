import Link from 'next/link';
import type { SourceItem } from '@/lib/apiClient';
import { buildHref, toggleCsv } from '@/lib/query';

/**
 * Multi-select source filter. Selection is stored in the `source` query
 * param as a comma-separated list (matches the API contract).
 */
export default function SourceFilter({
  sources,
  params,
  basePath,
}: {
  sources: SourceItem[];
  params: Record<string, string>;
  basePath: string;
}) {
  const selected = new Set((params.source ?? '').split(',').filter(Boolean));

  if (sources.length === 0) {
    return (
      <p className="text-xs text-neutral-500 dark:text-neutral-500">
        Source list unavailable.
      </p>
    );
  }

  return (
    <ul className="max-h-64 space-y-0.5 overflow-y-auto pr-1 text-sm">
      {sources.map((source) => {
        const active = selected.has(source.id);
        const next = toggleCsv(params.source, source.id);
        return (
          <li key={source.id}>
            <Link
              href={buildHref(basePath, params, { source: next, cursor: undefined })}
              aria-pressed={active}
              className={`flex items-center gap-2 rounded px-2 py-1 transition-colors hover:bg-neutral-100 dark:hover:bg-neutral-800 ${
                active ? 'font-medium text-brand-700 dark:text-brand-300' : ''
              }`}
            >
              <span
                aria-hidden
                className={`flex h-3.5 w-3.5 items-center justify-center rounded-sm border ${
                  active
                    ? 'border-brand-600 bg-brand-600 text-white'
                    : 'border-neutral-400 dark:border-neutral-600'
                }`}
              >
                {active && (
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="4" aria-hidden>
                    <path d="M20 6 9 17l-5-5" />
                  </svg>
                )}
              </span>
              <span className="truncate">{source.name}</span>
              <span className="ml-auto text-[10px] uppercase text-neutral-400">{source.lang}</span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
