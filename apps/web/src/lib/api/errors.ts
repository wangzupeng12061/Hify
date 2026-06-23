import type { components } from "./generated/schema";

export type HifyApiErrorPayload = components["schemas"]["ErrorResponse"];

const DEFAULT_ERROR_CODE = "api.request_failed";
const DEFAULT_ERROR_MESSAGE = "The API request failed.";

export class HifyApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly metadata: Record<string, unknown> | null;

  constructor(params: {
    code: string;
    message: string;
    status: number;
    metadata?: Record<string, unknown> | null;
    cause?: unknown;
  }) {
    super(params.message, { cause: params.cause });
    this.name = "HifyApiError";
    this.code = params.code;
    this.status = params.status;
    this.metadata = params.metadata ?? null;
  }
}

export function createApiError(params: {
  error: unknown;
  response: Pick<Response, "status">;
}): HifyApiError {
  const payload = parseApiErrorPayload(params.error);

  return new HifyApiError({
    code: payload?.detail.code ?? DEFAULT_ERROR_CODE,
    message: payload?.detail.message ?? DEFAULT_ERROR_MESSAGE,
    status: params.response.status,
    metadata: payload?.detail.metadata ?? null,
    cause: params.error,
  });
}

export function parseApiErrorPayload(error: unknown): HifyApiErrorPayload | null {
  if (!isRecord(error)) {
    return null;
  }

  const detail = error.detail;
  if (!isRecord(detail)) {
    return null;
  }

  if (typeof detail.code !== "string" || typeof detail.message !== "string") {
    return null;
  }

  const metadata = detail.metadata;
  if (metadata !== undefined && metadata !== null && !isRecord(metadata)) {
    return null;
  }

  return {
    detail: {
      code: detail.code,
      message: detail.message,
      metadata: metadata ?? null,
    },
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
