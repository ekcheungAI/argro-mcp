import { getArticle, type InsightResponse } from '@/lib/apiClient';

interface ResolvedArticle {
  title: string;
  url: string;
  sourceName: string;
}

/**
 * Renders a daily/weekly insight: title, summary, and sections. Linked
 * article ids in each section are resolved via GET /news/{id}; articles
 * that fail to resolve are shown as muted ids rather than breaking the page.
 */
export default async function InsightView({
  insight,
  lang,
}: {
  insight: InsightResponse;
  lang?: string;
}) {
  // Resolve all referenced article ids up front, in parallel.
  const ids = Array.from(new Set(insight.sections.flatMap((s) => s.articles)));
  const resolved = new Map<string, ResolvedArticle | null>(
    await Promise.all(
      ids.map(async (id): Promise<[string, ResolvedArticle | null]> => {
        try {
          const a = await getArticle(id, { lang });
          return [id, { title: a.title, url: a.url, sourceName: a.source.name }];
        } catch {
          return [id, null];
        }
      }),
    ),
  );

  return (
    <article className="space-y-6">
      <header className="card p-5">
        <p className="text-xs font-medium uppercase tracking-wide text-brand-600 dark:text-brand-400">
          {insight.type} insight · {insight.date} · {insight.lang}
        </p>
        <h1 className="mt-1 text-xl font-bold leading-tight">{insight.title}</h1>
        <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">{insight.summary}</p>
      </header>

      {insight.sections.map((section, i) => (
        <section key={i} className="card p-5">
          <h2 className="text-base font-semibold">{section.section_title}</h2>
          <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
            {section.content}
          </p>
          {section.articles.length > 0 && (
            <ul className="mt-3 space-y-1.5 border-t border-neutral-100 pt-3 text-sm dark:border-neutral-800">
              {section.articles.map((id) => {
                const article = resolved.get(id);
                return (
                  <li key={id} className="flex items-baseline gap-2">
                    <span aria-hidden className="text-brand-500">›</span>
                    {article ? (
                      <a
                        href={article.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:text-brand-700 dark:hover:text-brand-300"
                      >
                        {article.title}
                        <span className="ml-1.5 text-xs text-neutral-400">{article.sourceName}</span>
                      </a>
                    ) : (
                      <span className="text-neutral-400">Referenced article {id} unavailable</span>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      ))}
    </article>
  );
}
