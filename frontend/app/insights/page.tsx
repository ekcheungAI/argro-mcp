import { ApiError, getInsight, type InsightResponse } from '@/lib/apiClient';
import { normalizeParams, type RawSearchParams } from '@/lib/query';
import BackendUnavailable from '@/components/BackendUnavailable';
import DatePicker from '@/components/DatePicker';
import EmptyState from '@/components/EmptyState';
import InsightView from '@/components/InsightView';

export const metadata = { title: 'Daily Insight' };

export default async function InsightsPage({
  searchParams,
}: {
  searchParams: Promise<RawSearchParams>;
}) {
  const params = normalizeParams(await searchParams);
  const lang = params.lang;

  let insight: InsightResponse;
  try {
    insight = await getInsight({ type: 'daily', lang });
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return (
        <div className="space-y-4">
          <Header date={undefined} />
          <EmptyState
            title="No insight available yet"
            description="The daily insight has not been generated. Pick a past date to browse earlier insights."
          />
        </div>
      );
    }
    return <BackendUnavailable />;
  }

  return (
    <div className="space-y-4">
      <Header date={insight.date} />
      <InsightView insight={insight} lang={lang} />
    </div>
  );
}

function Header({ date }: { date?: string }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-lg font-bold">Daily insight</h1>
      <DatePicker value={date} />
    </div>
  );
}
