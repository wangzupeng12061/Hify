import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProvidersManagement } from "@/features/providers/components/providers-management";

const hookMocks = vi.hoisted(() => ({
  addProviderModel: vi.fn(),
  createProvider: vi.fn(),
  setProviderModelPricing: vi.fn(),
}));

vi.mock("@/features/providers/hooks", () => ({
  useAddProviderModel: () => ({
    data: undefined,
    error: null,
    isPending: false,
    mutateAsync: hookMocks.addProviderModel,
  }),
  useCreateProvider: () => ({
    data: undefined,
    error: null,
    isPending: false,
    mutateAsync: hookMocks.createProvider,
  }),
  useSetProviderModelPricing: () => ({
    data: undefined,
    error: null,
    isPending: false,
    mutateAsync: hookMocks.setProviderModelPricing,
  }),
}));

describe("ProvidersManagement", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("submits provider creation values", async () => {
    hookMocks.createProvider.mockResolvedValueOnce({});
    render(<ProvidersManagement />);

    fireEvent.change(screen.getByLabelText("Provider name"), {
      target: { value: "OpenAI" },
    });
    fireEvent.change(screen.getByLabelText("Provider type"), {
      target: { value: "openai" },
    });
    fireEvent.change(screen.getByLabelText("Base URL"), {
      target: { value: "https://api.openai.com/v1" },
    });
    fireEvent.change(screen.getByLabelText("Credential plaintext"), {
      target: { value: "secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create provider" }));

    await waitFor(() =>
      expect(hookMocks.createProvider).toHaveBeenCalledWith({
        base_url: "https://api.openai.com/v1",
        credential_plaintext: "secret",
        name: "OpenAI",
        provider_type: "openai",
      }),
    );
  });

  it("submits model creation values with numeric parsing", async () => {
    hookMocks.addProviderModel.mockResolvedValueOnce({});
    render(<ProvidersManagement />);

    fireEvent.change(screen.getByLabelText("Provider ID"), {
      target: { value: "provider-1" },
    });
    fireEvent.change(screen.getByLabelText("Model name"), {
      target: { value: "gpt-4.1" },
    });
    fireEvent.change(screen.getByLabelText("Display name"), {
      target: { value: "GPT-4.1" },
    });
    fireEvent.change(screen.getByLabelText("Context window tokens"), {
      target: { value: "128000" },
    });
    fireEvent.click(screen.getByLabelText("Supports structured output"));
    fireEvent.click(screen.getByRole("button", { name: "Add model" }));

    await waitFor(() =>
      expect(hookMocks.addProviderModel).toHaveBeenCalledWith({
        context_window_tokens: 128000,
        display_name: "GPT-4.1",
        kind: "chat",
        model_name: "gpt-4.1",
        providerId: "provider-1",
        supports_structured_output: true,
        supports_tools: true,
        supports_vision: false,
      }),
    );
  });

  it("submits model pricing values with nullable empty prices", async () => {
    hookMocks.setProviderModelPricing.mockResolvedValueOnce({});
    render(<ProvidersManagement />);

    fireEvent.change(screen.getByLabelText("Model ID"), {
      target: { value: "model-1" },
    });
    fireEvent.change(screen.getByLabelText("Price per 1M input tokens"), {
      target: { value: "2.5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Set pricing" }));

    await waitFor(() =>
      expect(hookMocks.setProviderModelPricing).toHaveBeenCalledWith({
        modelId: "model-1",
        price_per_1m_input_tokens: 2.5,
        price_per_1m_output_tokens: null,
      }),
    );
  });
});
