/** Helpers for working with Next.js searchParams. */

export type RawSearchParams = Record<string, string | string[] | undefined>;
export type QueryMap = Record<string, string | undefined>;

/** Take the first value if a param is repeated. */
export function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

/** Normalize Next.js searchParams into a flat string map (empty values dropped). */
export function normalizeParams(raw: RawSearchParams): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(raw)) {
    const v = first(value);
    if (v !== undefined && v !== '') out[key] = v;
  }
  return out;
}

/** Build a query string, skipping undefined/empty values. */
export function toQueryString(params: QueryMap): string {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') qs.set(key, value);
  }
  return qs.toString();
}

/**
 * Toggle a value inside a comma-separated query param (multi-select filters).
 * Returns the new csv value, or undefined if nothing remains selected.
 */
export function toggleCsv(csv: string | undefined, value: string): string | undefined {
  const set = new Set(
    (csv ?? '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean),
  );
  if (set.has(value)) set.delete(value);
  else set.add(value);
  return set.size ? Array.from(set).join(',') : undefined;
}

/** Merge param overrides into a base map and produce path + query string. */
export function buildHref(
  path: string,
  base: Record<string, string>,
  overrides: QueryMap,
): string {
  const merged: Record<string, string> = { ...base };
  for (const [key, value] of Object.entries(overrides)) {
    if (value === undefined || value === '') delete merged[key];
    else merged[key] = value;
  }
  const qs = toQueryString(merged);
  return qs ? `${path}?${qs}` : path;
}
