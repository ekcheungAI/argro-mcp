import Link from 'next/link';
import EmptyState from '@/components/EmptyState';

export default function NotFound() {
  return (
    <EmptyState
      title="Page not found"
      description="The page you are looking for does not exist."
      action={
        <Link
          href="/"
          className="text-sm font-medium text-brand-700 hover:underline dark:text-brand-300"
        >
          Back to Today →
        </Link>
      }
    />
  );
}
