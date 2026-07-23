'use client';

import { usePathname, useRouter, useSearchParams } from 'next/navigation';

const LANGS = [
  { code: 'en', label: 'EN' },
  { code: 'zh-TW', label: '繁中' },
];

/**
 * Language switcher backed by the `?lang=` query param (SSR-friendly: the
 * server re-renders with translated fields). `en` is the default, so it
 * removes the param; all other params are preserved.
 *
 * Must be rendered inside a <Suspense> boundary (uses useSearchParams).
 */
export default function LangSwitch() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const current = searchParams.get('lang') ?? 'en';

  const select = (code: string) => {
    const next = new URLSearchParams(searchParams.toString());
    if (code === 'en') next.delete('lang');
    else next.set('lang', code);
    const qs = next.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
  };

  return (
    <div
      role="group"
      aria-label="Language"
      className="flex overflow-hidden rounded-md border border-neutral-300 text-xs dark:border-neutral-700"
    >
      {LANGS.map((l) => (
        <button
          key={l.code}
          type="button"
          onClick={() => select(l.code)}
          aria-pressed={current === l.code}
          className={`px-2 py-1 font-medium transition-colors ${
            current === l.code
              ? 'bg-brand-600 text-white'
              : 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800'
          }`}
        >
          {l.label}
        </button>
      ))}
    </div>
  );
}
