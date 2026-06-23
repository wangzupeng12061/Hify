import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { hifyApiClient } from "@/lib/api/client";
import { createHifyQueryClient } from "@/lib/query/query-client";
import {
  useAddProviderModel,
  useCreateProvider,
  useSetProviderModelPricing,
} from "@/features/providers";
import type { Model } from "@/features/providers";

const apiClientMock = vi.hoisted(() => ({
  POST: vi.fn(),
  PUT: vi.fn(),
}));

vi.mock("@/lib/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/client")>();

  return {
    ...actual,
    hifyApiClient: apiClientMock,
  };
});

describe("provider hooks", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("creates providers with the backend request contract", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: {
        base_url: null,
        id: "provider-1",
        name: "OpenAI",
        provider_type: "openai",
        status: "active",
        team_id: "team-1",
      },
      response: new Response(null, { status: 201 }),
    });

    const { result } = renderHook(() => useCreateProvider(), {
      wrapper: createQueryWrapper(),
    });

    const provider = await result.current.mutateAsync({
      base_url: null,
      credential_plaintext: "secret",
      name: "OpenAI",
      provider_type: "openai",
    });

    expect(hifyApiClient.POST).toHaveBeenCalledWith("/providers", {
      body: {
        base_url: null,
        credential_plaintext: "secret",
        name: "OpenAI",
        provider_type: "openai",
      },
    });
    expect(provider.id).toBe("provider-1");
  });

  it("adds provider models with path params", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: createModelResponse(),
      response: new Response(null, { status: 201 }),
    });

    const { result } = renderHook(() => useAddProviderModel(), {
      wrapper: createQueryWrapper(),
    });

    await result.current.mutateAsync({
      context_window_tokens: 128000,
      display_name: "GPT-4.1",
      kind: "chat",
      model_name: "gpt-4.1",
      providerId: "provider-1",
      supports_structured_output: true,
      supports_tools: true,
      supports_vision: false,
    });

    expect(hifyApiClient.POST).toHaveBeenCalledWith("/providers/{provider_id}/models", {
      body: {
        context_window_tokens: 128000,
        display_name: "GPT-4.1",
        kind: "chat",
        model_name: "gpt-4.1",
        supports_structured_output: true,
        supports_tools: true,
        supports_vision: false,
      },
      params: {
        path: {
          provider_id: "provider-1",
        },
      },
    });
  });

  it("sets provider model pricing with path params", async () => {
    apiClientMock.PUT.mockResolvedValueOnce({
      data: createModelResponse({
        price_per_1m_input_tokens: "2.5",
        price_per_1m_output_tokens: "10",
      }),
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useSetProviderModelPricing(), {
      wrapper: createQueryWrapper(),
    });

    await result.current.mutateAsync({
      modelId: "model-1",
      price_per_1m_input_tokens: 2.5,
      price_per_1m_output_tokens: 10,
    });

    expect(hifyApiClient.PUT).toHaveBeenCalledWith("/providers/models/{model_id}/pricing", {
      body: {
        price_per_1m_input_tokens: 2.5,
        price_per_1m_output_tokens: 10,
      },
      params: {
        path: {
          model_id: "model-1",
        },
      },
    });
  });
});

function createQueryWrapper() {
  const queryClient = createHifyQueryClient();

  return function QueryWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function createModelResponse(override: Partial<Model> = {}): Model {
  return {
    context_window_tokens: 128000,
    display_name: "GPT-4.1",
    id: "model-1",
    kind: "chat",
    model_name: "gpt-4.1",
    price_per_1m_input_tokens: null,
    price_per_1m_output_tokens: null,
    provider_id: "provider-1",
    provider_name: "OpenAI",
    provider_type: "openai",
    status: "active",
    supports_structured_output: true,
    supports_tools: true,
    supports_vision: false,
    team_id: "team-1",
    ...override,
  };
}
