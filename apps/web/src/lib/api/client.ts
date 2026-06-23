import createClient, { type Client } from "openapi-fetch";

import { createApiError } from "./errors";
import type { paths } from "./generated/schema";

const DEFAULT_API_BASE_URL = "/api";

export type HifyApiClient = Client<paths>;

export function createHifyApiClient(params: {
  baseUrl?: string;
  fetch?: (input: Request) => Promise<Response>;
  headers?: HeadersInit;
} = {}): HifyApiClient {
  return createClient<paths>({
    baseUrl: normalizeApiBaseUrl(params.baseUrl ?? getConfiguredApiBaseUrl()),
    fetch: params.fetch,
    headers: params.headers,
  });
}

export function getConfiguredApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_HIFY_API_BASE_URL ?? DEFAULT_API_BASE_URL;
}

export function normalizeApiBaseUrl(baseUrl: string): string {
  const trimmedBaseUrl = baseUrl.trim();
  if (trimmedBaseUrl === "") {
    return DEFAULT_API_BASE_URL;
  }

  return trimmedBaseUrl.replace(/\/+$/, "");
}

export async function unwrapApiResponse<T>(result: {
  data?: T;
  error?: unknown;
  response: Response;
}): Promise<T> {
  if (result.error !== undefined) {
    throw createApiError({ error: result.error, response: result.response });
  }

  if (result.data === undefined) {
    throw createApiError({ error: null, response: result.response });
  }

  return result.data;
}

export const hifyApiClient = createHifyApiClient();
