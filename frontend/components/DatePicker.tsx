'use client';

import { useRouter } from 'next/navigation';

/**
 * Date picker that navigates to /insights/[date] when a date is chosen.
 */
export default function DatePicker({ value }: { value?: string }) {
  const router = useRouter();
  const today = new Date().toISOString().slice(0, 10);

  return (
    <label className="flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
      <span>Jump to date</span>
      <input
        type="date"
        value={value ?? ''}
        max={today}
        onChange={(e) => {
          if (e.target.value) router.push(`/insights/${e.target.value}`);
        }}
        className="rounded-md border border-neutral-300 bg-white px-2 py-1 text-sm text-neutral-900 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100"
      />
    </label>
  );
}
