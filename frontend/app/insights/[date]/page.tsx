import { notFound } from 'next/navigation';
import { ApiError, getInsight, type InsightResponse } from '@/lib/apiClient';
import { normalizeParams, type RawSearchParams } from '@/lib/query';
import BackendUnavailable from '@/components/BackendUnavailable';
import DatePicker from '@/components/DatePicker';
import EmptyState from '@/components/EmptyState';
import InsightView from '@/components/InsightView';

export const metadata = { title: 'Daily Insight' };

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function isValidDate(date: string): boolean {
  if (!DATE_RE.test(date)) return false;
  const d = new Date(`${date}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === date;
}

export default async function InsightDatePage({
  params,
  searchParams,
}: {
  params: Promise<{ date: string }>;
  searchParams: Promise<RawSearchParams>;
}) {
  const { date } = await params;
  if (!isValidDate(date)) notFound();

  const sp = normalizeParams(await searchParams);
  const lang = sp.lang;

  let insight: InsightResponse;
  try {
    insight = await getInsight({ type: 'daily', date, lang });
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-lg font-bold">Daily insight · {date}</h1>
            <DatePicker value={date} />
          </div>
          <EmptyState
            title={`No insight for ${date}`}
            description="No insight was generated for this date. Try another day."
          />
        </div>
      );
    }
    return <BackendUnavailable />;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-bold">Daily insight · {insight.date}</h1>
        <DatePicker value={insight.date} />
      </div>
      <InsightView insight={insight} lang={lang} />
    </div>
  );
}
