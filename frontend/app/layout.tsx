import type { Metadata } from 'next';
import Link from 'next/link';
import { Suspense } from 'react';
import './globals.css';
import LangSwitch from '@/components/LangSwitch';
import NavLinks from '@/components/NavLinks';
import ThemeToggle from '@/components/ThemeToggle';

export const metadata: Metadata = {
  title: {
    default: 'AIGRO — AI News, Aggregated',
    template: '%s · AIGRO',
  },
  description:
    'AIGRO aggregates AI news from multiple sources: daily hot lists, full stream with filters, structured daily insights, and an agent-ready HTTP API + MCP server.',
};

// Pre-paint theme script: applies the saved/system theme before first paint
// to avoid a flash of the wrong theme (FOUC).
const themeScript = `(function(){try{var t=localStorage.getItem('aigro-theme');var d=t?t==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;var c=document.documentElement.classList;if(d){c.add('dark')}else{c.remove('dark')}}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="flex min-h-screen flex-col">
        <header className="sticky top-0 z-20 border-b border-neutral-200 bg-white/90 backdrop-blur dark:border-neutral-800 dark:bg-neutral-950/90">
          <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4">
            <Link href="/" className="flex shrink-0 items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-600 text-sm font-bold text-white">
                A
              </span>
              <span className="text-lg font-bold tracking-tight">AIGRO</span>
            </Link>
            <div className="overflow-x-auto">
              <NavLinks />
            </div>
            <div className="ml-auto flex shrink-0 items-center gap-2">
              <Suspense fallback={null}>
                <LangSwitch />
              </Suspense>
              <ThemeToggle />
            </div>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>
        <footer className="border-t border-neutral-200 py-4 text-center text-xs text-neutral-500 dark:border-neutral-800 dark:text-neutral-500">
          AIGRO · multi-source AI news aggregation · HTTP API &amp; MCP ready
        </footer>
      </body>
    </html>
  );
}
