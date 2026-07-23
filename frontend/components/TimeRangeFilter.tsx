import Link from 'next/link';
import { buildHref } from '@/lib/query';

const RANGES = [
  { key: '24h', label: 'Last 24h' },
  { key: '7d', label: 'Last 7 days' },
] as const;

/**
 * Time range filter for the /all stream: quick ranges (24h / 7d) plus a
 * custom from/to form (plain GET form, works without client JS).
 * The page maps `range`/`from`/`to` onto the API's `from`/`to` params.
 */
export default function TimeRangeFilter({
  params,
  basePath,
}: {
  params: Record<string, string>;
  basePath: string;
}) {
  const current = params.range ?? '24h';
  const hidden = Object.entries(params).filter(
    ([k]) => !['range', 'from', 'to', 'cursor'].includes(k),
  );

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {RANGES.map((r) => (
          <Link
            key={r.key}
            href={buildHref(basePath, params, {
              range: r.key === '24h' ? undefined : r.key,
              from: undefined,
              to: undefined,
              cursor: undefined,
            })}
            aria-pressed={current === r.key}
            className={`chip ${current === r.key ? 'chip-active' : ''}`}
          >
            {r.label}
          </Link>
        ))}
      </div>
      <form action={basePath} method="get" className="space-y-1.5">
        {hidden.map(([k, v]) => (
          <input key={k} type="hidden" name={k} value={v} />
        ))}
        <input type="hidden" name="range" value="custom" />
        <label className="block text-xs text-neutral-500 dark:text-neutral-400">
          From
          <input
            type="date"
            name="from"
            defaultValue={current === 'custom' ? params.from : undefined}
            className="mt-0.5 block w-full rounded border border-neutral-300 bg-white px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
        </label>
        <label className="block text-xs text-neutral-500 dark:text-neutral-400">
          To
          <input
            type="date"
            name="to"
            defaultValue={current === 'custom' ? params.to : undefined}
            className="mt-0.5 block w-full rounded border border-neutral-300 bg-white px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
        </label>
        <button
          type="submit"
          className={`chip w-full justify-center ${current === 'custom' ? 'chip-active' : ''}`}
        >
          Apply custom range
        </button>
      </form>
    </div>
  );
}
