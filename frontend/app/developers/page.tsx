import type { Metadata } from 'next';
import type { ReactNode } from 'react';

export const metadata: Metadata = {
  title: 'Developers & Agents',
  description: 'AIGRO HTTP API reference, MCP server connection info, and example agent prompts.',
};

function Code({ children }: { children: string }) {
  return (
    <pre className="mt-2 overflow-x-auto rounded-md bg-neutral-900 p-3 text-xs leading-relaxed text-neutral-100 dark:bg-neutral-800">
      <code>{children}</code>
    </pre>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="card p-5">
      <h2 className="text-base font-semibold">{title}</h2>
      <div className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">{children}</div>
    </section>
  );
}

const ENDPOINTS = [
  {
    method: 'GET',
    path: '/news/stream',
    desc: 'Paginated news stream. Params: from, to, lang, topic, source, q, sort (time_desc|hot_desc), limit (max 200), cursor.',
    curl: `curl "$API_BASE/news/stream?from=2026-07-22&topic=model_release&limit=20"`,
  },
  {
    method: 'GET',
    path: '/news/hot',
    desc: 'Hot articles for a date, sorted by hot_score. Params: date, lang, topic, limit (max 100).',
    curl: `curl "$API_BASE/news/hot?date=2026-07-23&lang=en&limit=30"`,
  },
  {
    method: 'GET',
    path: '/news/{id}',
    desc: 'Full article detail incl. content, topics with confidence, and cluster-related articles. Params: lang.',
    curl: `curl "$API_BASE/news/ARTICLE_ID?lang=zh-TW"`,
  },
  {
    method: 'GET',
    path: '/insights/daily',
    desc: 'Structured daily/weekly insight with sections and linked article ids. Params: type (daily|weekly), date, lang.',
    curl: `curl "$API_BASE/insights/daily?type=daily&date=2026-07-23"`,
  },
  {
    method: 'GET',
    path: '/meta/sources',
    desc: 'List of active ingestion sources (id, name, type, lang, homepage/feed URLs).',
    curl: `curl "$API_BASE/meta/sources"`,
  },
  {
    method: 'GET',
    path: '/meta/topics',
    desc: 'Topic taxonomy (key, name, description) used by the topic filters.',
    curl: `curl "$API_BASE/meta/topics"`,
  },
];

const TOOLS = [
  {
    name: 'get_daily_hot',
    desc: 'Hot AI news list for a date/language. Inputs: date?, lang?, limit (default 30).',
  },
  {
    name: 'search_news',
    desc: 'Natural-language news search. Inputs: query (required), lang?, from?, to?, topic?, limit (default 20).',
  },
  {
    name: 'get_article_detail',
    desc: 'Full detail for one article. Inputs: id (required), lang?.',
  },
  {
    name: 'get_insight',
    desc: 'Structured daily/weekly brief. Inputs: type (daily|weekly), date?, lang?.',
  },
];

const PROMPTS = [
  'Summarize today’s top 10 AI news items in Traditional Chinese, grouped by topic.',
  'Search for news about “open-weight models” from the last 7 days and rank the 5 most significant releases.',
  'Get the full detail of the top hot article today and explain why it matters for LLM infrastructure.',
  'Fetch today’s daily insight and turn each section into a one-line briefing for a Slack digest.',
];

export default function DevelopersPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-bold">Developers &amp; Agents</h1>
        <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
          Everything on AIGRO is machine-readable: a REST HTTP API for apps and a
          streamable-HTTP MCP server for AI agents.
        </p>
      </div>

      <Section title="HTTP API">
        <p>
          Base URL: <code className="rounded bg-neutral-100 px-1 dark:bg-neutral-800">https://api.ai-news-platform.com/v1</code>{' '}
          (self-hosted default: <code className="rounded bg-neutral-100 px-1 dark:bg-neutral-800">http://localhost:8000</code>).
          All responses are JSON. Private deployments authenticate with{' '}
          <code className="rounded bg-neutral-100 px-1 dark:bg-neutral-800">X-API-Key: &lt;token&gt;</code>.
        </p>
        <div className="mt-4 space-y-4">
          {ENDPOINTS.map((e) => (
            <div key={e.path}>
              <p className="font-mono text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                <span className="mr-2 rounded bg-brand-100 px-1.5 py-0.5 text-xs text-brand-800 dark:bg-brand-950 dark:text-brand-200">
                  {e.method}
                </span>
                {e.path}
              </p>
              <p className="mt-1">{e.desc}</p>
              <Code>{e.curl}</Code>
            </div>
          ))}
        </div>
      </Section>

      <Section title="MCP server (ai-news-mcp-server)">
        <p>
          The MCP server is stateless and speaks <strong>streamable HTTP</strong> at{' '}
          <code className="rounded bg-neutral-100 px-1 dark:bg-neutral-800">/mcp</code>. Point any
          MCP-capable client at it:
        </p>
        <Code>{`{
  "mcpServers": {
    "aigro-news": {
      "type": "streamable-http",
      "url": "https://your-aigro-host/mcp"
    }
  }
}`}</Code>
        <p className="mt-3 font-medium text-neutral-900 dark:text-neutral-100">Tools</p>
        <ul className="mt-2 space-y-2">
          {TOOLS.map((t) => (
            <li key={t.name}>
              <code className="rounded bg-neutral-100 px-1 font-semibold text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100">
                {t.name}
              </code>{' '}
              — {t.desc}
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Example agent prompts">
        <ul className="list-disc space-y-1.5 pl-5">
          {PROMPTS.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      </Section>
    </div>
  );
}
