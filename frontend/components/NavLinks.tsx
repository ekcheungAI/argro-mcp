'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const LINKS = [
  { href: '/', label: 'Today' },
  { href: '/all', label: 'All' },
  { href: '/insights', label: 'Insights' },
  { href: '/developers', label: 'Developers' },
];

export default function NavLinks() {
  const pathname = usePathname();

  return (
    <nav className="flex items-center gap-1 text-sm" aria-label="Main">
      {LINKS.map((link) => {
        const active =
          link.href === '/' ? pathname === '/' : pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? 'page' : undefined}
            className={`rounded-md px-2.5 py-1.5 font-medium transition-colors ${
              active
                ? 'bg-brand-100 text-brand-800 dark:bg-brand-950 dark:text-brand-200'
                : 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800'
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
