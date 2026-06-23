import { describe, expect, it } from "vitest";

import { HifyApiError } from "@/lib/api/errors";
import { createHifyQueryClient, shouldRetryQuery } from "@/lib/query/query-client";

describe("Hify query client", () => {
  it("uses bounded retries for server failures only", () => {
    const serverError = new HifyApiError({
      code: "api.unavailable",
      message: "API unavailable.",
      status: 503,
    });
    const permissionError = new HifyApiError({
      code: "identity.permission_denied",
      message: "Permission denied.",
      status: 403,
    });

    expect(shouldRetryQuery(0, serverError)).toBe(true);
    expect(shouldRetryQuery(2, serverError)).toBe(false);
    expect(shouldRetryQuery(0, permissionError)).toBe(false);
  });

  it("creates a QueryClient with Hify defaults", () => {
    const queryClient = createHifyQueryClient();
    const queryOptions = queryClient.getDefaultOptions().queries;

    expect(queryOptions?.staleTime).toBe(30_000);
    expect(queryOptions?.refetchOnWindowFocus).toBe(false);
  });
});
