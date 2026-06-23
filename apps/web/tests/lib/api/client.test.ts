import { describe, expect, it } from "vitest";

import {
  createHifyApiClient,
  getConfiguredApiBaseUrl,
  normalizeApiBaseUrl,
  unwrapApiResponse,
} from "@/lib/api/client";
import { HifyApiError, parseApiErrorPayload } from "@/lib/api/errors";

describe("API client configuration", () => {
  it("normalizes blank and trailing-slash base URLs", () => {
    expect(normalizeApiBaseUrl("")).toBe("/api");
    expect(normalizeApiBaseUrl("   ")).toBe("/api");
    expect(normalizeApiBaseUrl("https://api.example.com///")).toBe("https://api.example.com");
  });

  it("uses the public environment base URL when configured", () => {
    const previousBaseUrl = process.env.NEXT_PUBLIC_HIFY_API_BASE_URL;
    process.env.NEXT_PUBLIC_HIFY_API_BASE_URL = "https://api.example.com";

    try {
      expect(getConfiguredApiBaseUrl()).toBe("https://api.example.com");
    } finally {
      if (previousBaseUrl === undefined) {
        delete process.env.NEXT_PUBLIC_HIFY_API_BASE_URL;
      } else {
        process.env.NEXT_PUBLIC_HIFY_API_BASE_URL = previousBaseUrl;
      }
    }
  });

  it("creates a typed OpenAPI client", () => {
    const client = createHifyApiClient({ baseUrl: "/backend" });

    expect(typeof client.GET).toBe("function");
    expect(typeof client.POST).toBe("function");
  });
});

describe("API errors", () => {
  it("parses the backend error response contract", () => {
    const payload = parseApiErrorPayload({
      detail: {
        code: "runs.not_found",
        message: "Run not found.",
        metadata: { run_id: "run_1" },
      },
    });

    expect(payload).toEqual({
      detail: {
        code: "runs.not_found",
        message: "Run not found.",
        metadata: { run_id: "run_1" },
      },
    });
  });

  it("rejects unknown error payloads", () => {
    expect(parseApiErrorPayload({ message: "failed" })).toBeNull();
    expect(parseApiErrorPayload(null)).toBeNull();
  });

  it("throws a stable HifyApiError for API failures", async () => {
    const response = new Response(null, { status: 403 });

    await expect(
      unwrapApiResponse({
        error: {
          detail: {
            code: "identity.permission_denied",
            message: "Permission denied.",
          },
        },
        response,
      }),
    ).rejects.toMatchObject({
      code: "identity.permission_denied",
      message: "Permission denied.",
      status: 403,
    });
  });

  it("throws a generic HifyApiError when data and error are both missing", async () => {
    const response = new Response(null, { status: 502 });

    await expect(
      unwrapApiResponse({
        response,
      }),
    ).rejects.toBeInstanceOf(HifyApiError);
  });
});
