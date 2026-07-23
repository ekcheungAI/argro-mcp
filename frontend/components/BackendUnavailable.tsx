import EmptyState from './EmptyState';
import { API_BASE_URL } from '@/lib/apiClient';

export default function BackendUnavailable() {
  return (
    <EmptyState
      title="Backend unavailable"
      description={`Could not reach the AIGRO API at ${API_BASE_URL}. Make sure the backend is running and NEXT_PUBLIC_API_BASE_URL is configured correctly, then reload this page.`}
    />
  );
}
