/**
 * Format an ISO8601 timestamp as a compact relative time, e.g. "3h ago".
 * Falls back to a YYYY-MM-DD date for items older than a week, and to the
 * raw input if it cannot be parsed.
 */
export function formatRelativeTime(iso: string, now: Date = new Date()): string {
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return iso;

  const diffMs = now.getTime() - ts;
  if (diffMs < 0) return 'just now';

  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;

  return new Date(ts).toISOString().slice(0, 10);
}
