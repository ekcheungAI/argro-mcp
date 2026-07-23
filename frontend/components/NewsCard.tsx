import { formatRelativeTime } from '@/lib/time';

export interface NewsCardProps {
  title: string;
  summary?: string | null;
  sourceName: string;
  publishedAt: string;
  topics: string[];
  lang: string;
  originalLang: string;
  url: string;
  /** The user's currently selected language, used for the lang badge rule. */
  userLang?: string;
  hotScore?: number;
}

function humanizeTopic(key: string): string {
  return key.replace(/_/g, ' ');
}

export default function NewsCard({
  title,
  summary,
  sourceName,
  publishedAt,
  topics,
  lang,
  originalLang,
  url,
  userLang,
  hotScore,
}: NewsCardProps) {
  // Badge rule (06 §2): show when the displayed language differs from the
  // article's original language (translated) or from the user's selection.
  const showLangBadge =
    lang !== originalLang || (userLang !== undefined && lang !== userLang);

  return (
    <article className="card p-4 transition-colors hover:border-brand-400 dark:hover:border-brand-700">
      <div className="flex items-start justify-between gap-3">
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium leading-snug hover:text-brand-700 dark:hover:text-brand-300"
        >
          {title}
        </a>
        {showLangBadge && (
          <span className="shrink-0 rounded border border-neutral-300 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-neutral-500 dark:border-neutral-700 dark:text-neutral-400">
            {lang}
          </span>
        )}
      </div>
      {summary && (
        <p className="mt-1.5 line-clamp-3 text-sm text-neutral-600 dark:text-neutral-400">
          {summary}
        </p>
      )}
      <div className="mt-2.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-neutral-500 dark:text-neutral-500">
        <span className="font-medium text-neutral-700 dark:text-neutral-300">{sourceName}</span>
        <span aria-hidden>·</span>
        <time dateTime={publishedAt}>{formatRelativeTime(publishedAt)}</time>
        {hotScore !== undefined && (
          <>
            <span aria-hidden>·</span>
            <span title="Hot score" className="text-brand-600 dark:text-brand-400">
              hot {hotScore.toFixed(2)}
            </span>
          </>
        )}
        {topics.length > 0 && (
          <span className="flex flex-wrap gap-1">
            {topics.map((t) => (
              <span
                key={t}
                className="rounded-full bg-brand-50 px-2 py-0.5 text-brand-800 dark:bg-brand-950 dark:text-brand-300"
              >
                {humanizeTopic(t)}
              </span>
            ))}
          </span>
        )}
      </div>
    </article>
  );
}
