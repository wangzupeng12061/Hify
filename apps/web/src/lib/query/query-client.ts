import { QueryClient } from "@tanstack/react-query";

import { HifyApiError } from "@/lib/api/errors";

const QUERY_STALE_TIME_MS = 30_000;
const MAX_QUERY_RETRY_COUNT = 2;

export function createHifyQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        retry: shouldRetryQuery,
        staleTime: QUERY_STALE_TIME_MS,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  if (failureCount >= MAX_QUERY_RETRY_COUNT) {
    return false;
  }

  if (error instanceof HifyApiError) {
    return error.status >= 500;
  }

  return true;
}
