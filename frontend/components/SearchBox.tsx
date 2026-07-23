/**
 * Search box mapping to the `q` query param. Plain GET form so it works
 * without client-side JS; other active filters are preserved via hidden
 * inputs (except cursor, which must reset on a new search).
 */
export default function SearchBox({
  value,
  params,
  basePath,
}: {
  value?: string;
  params: Record<string, string>;
  basePath: string;
}) {
  const hidden = Object.entries(params).filter(([k]) => !['q', 'cursor'].includes(k));

  return (
    <form action={basePath} method="get" className="flex gap-2">
      {hidden.map(([k, v]) => (
        <input key={k} type="hidden" name={k} value={v} />
      ))}
      <input
        type="search"
        name="q"
        defaultValue={value}
        placeholder="Search AI news…"
        className="w-full rounded-md border border-neutral-300 bg-white px-3 py-1.5 text-sm placeholder:text-neutral-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-neutral-700 dark:bg-neutral-900"
      />
      <button
        type="submit"
        className="shrink-0 rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
      >
        Search
      </button>
    </form>
  );
}
