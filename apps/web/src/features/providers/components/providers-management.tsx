"use client";

import { useMemo, useState, type FormEvent } from "react";

import { HifyApiError } from "@/lib/api/errors";

import {
  useAddProviderModel,
  useCreateProvider,
  useSetProviderModelPricing,
} from "../hooks";
import type { Model, Provider } from "../types";

type ProviderFormState = {
  baseUrl: string;
  credentialPlaintext: string;
  name: string;
  providerType: string;
};

type ModelFormState = {
  contextWindowTokens: string;
  displayName: string;
  kind: string;
  modelName: string;
  providerId: string;
  supportsStructuredOutput: boolean;
  supportsTools: boolean;
  supportsVision: boolean;
};

type PricingFormState = {
  modelId: string;
  pricePer1mInputTokens: string;
  pricePer1mOutputTokens: string;
};

const initialProviderForm: ProviderFormState = {
  baseUrl: "",
  credentialPlaintext: "",
  name: "",
  providerType: "openai",
};

const initialModelForm: ModelFormState = {
  contextWindowTokens: "128000",
  displayName: "",
  kind: "chat",
  modelName: "",
  providerId: "",
  supportsStructuredOutput: false,
  supportsTools: true,
  supportsVision: false,
};

const initialPricingForm: PricingFormState = {
  modelId: "",
  pricePer1mInputTokens: "",
  pricePer1mOutputTokens: "",
};

export function ProvidersManagement() {
  const createProviderMutation = useCreateProvider();
  const addProviderModelMutation = useAddProviderModel();
  const setProviderModelPricingMutation = useSetProviderModelPricing();
  const [formError, setFormError] = useState<string | null>(null);
  const [providerForm, setProviderForm] = useState(initialProviderForm);
  const [modelForm, setModelForm] = useState(initialModelForm);
  const [pricingForm, setPricingForm] = useState(initialPricingForm);

  const latestProvider = createProviderMutation.data;
  const latestModel = addProviderModelMutation.data ?? setProviderModelPricingMutation.data;

  async function handleCreateProvider(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    try {
      await createProviderMutation.mutateAsync({
        base_url: providerForm.baseUrl.trim() || null,
        credential_plaintext: providerForm.credentialPlaintext,
        name: providerForm.name.trim(),
        provider_type: providerForm.providerType.trim(),
      });
    } catch {
      return;
    }
  }

  async function handleAddModel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    try {
      await addProviderModelMutation.mutateAsync({
        context_window_tokens: parseRequiredPositiveInteger(
          modelForm.contextWindowTokens,
          "Context window",
        ),
        display_name: modelForm.displayName.trim(),
        kind: modelForm.kind.trim(),
        model_name: modelForm.modelName.trim(),
        providerId: modelForm.providerId.trim(),
        supports_structured_output: modelForm.supportsStructuredOutput,
        supports_tools: modelForm.supportsTools,
        supports_vision: modelForm.supportsVision,
      });
    } catch (error) {
      if (!(error instanceof HifyApiError)) {
        setFormError(error instanceof Error ? error.message : "Unable to add model.");
      }
    }
  }

  async function handleSetPricing(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    try {
      await setProviderModelPricingMutation.mutateAsync({
        modelId: pricingForm.modelId.trim(),
        price_per_1m_input_tokens: parseOptionalNonNegativeNumber(
          pricingForm.pricePer1mInputTokens,
          "Input token price",
        ),
        price_per_1m_output_tokens: parseOptionalNonNegativeNumber(
          pricingForm.pricePer1mOutputTokens,
          "Output token price",
        ),
      });
    } catch (error) {
      if (!(error instanceof HifyApiError)) {
        setFormError(error instanceof Error ? error.message : "Unable to set pricing.");
      }
    }
  }

  const operationError =
    createProviderMutation.error ??
    addProviderModelMutation.error ??
    setProviderModelPricingMutation.error;
  const isSubmitting =
    createProviderMutation.isPending ||
    addProviderModelMutation.isPending ||
    setProviderModelPricingMutation.isPending;

  return (
    <div className="page-stack">
      <section className="hero">
        <p className="hero__eyebrow">Providers</p>
        <h2>Configure model providers and model pricing.</h2>
        <p>
          This page uses the current backend contract: create providers, add models, and set model
          pricing. Listing providers will be added when the backend exposes read APIs.
        </p>
      </section>

      {formError ? <ProviderErrorBanner message={formError} /> : null}
      {operationError ? <ProviderErrorBanner error={operationError} /> : null}

      <section className="provider-layout">
        <ProviderForm
          form={providerForm}
          isSubmitting={createProviderMutation.isPending}
          onChange={setProviderForm}
          onSubmit={handleCreateProvider}
          provider={latestProvider}
        />
        <ModelForm
          form={modelForm}
          isSubmitting={addProviderModelMutation.isPending}
          model={addProviderModelMutation.data}
          onChange={setModelForm}
          onSubmit={handleAddModel}
        />
        <PricingForm
          form={pricingForm}
          isSubmitting={setProviderModelPricingMutation.isPending}
          model={setProviderModelPricingMutation.data}
          onChange={setPricingForm}
          onSubmit={handleSetPricing}
        />
      </section>

      <ProviderSummary isSubmitting={isSubmitting} model={latestModel} provider={latestProvider} />
    </div>
  );
}

function ProviderForm({
  form,
  isSubmitting,
  onChange,
  onSubmit,
  provider,
}: {
  form: ProviderFormState;
  isSubmitting: boolean;
  onChange: (form: ProviderFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  provider?: Provider;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Step 1</p>
      <h2>Create provider</h2>
      <label className="form-field">
        Provider name
        <input
          name="name"
          onChange={(event) => onChange({ ...form, name: event.target.value })}
          required
          value={form.name}
        />
      </label>
      <label className="form-field">
        Provider type
        <select
          name="providerType"
          onChange={(event) => onChange({ ...form, providerType: event.target.value })}
          required
          value={form.providerType}
        >
          <option value="openai">OpenAI</option>
          <option value="anthropic">Claude</option>
          <option value="deepseek">DeepSeek</option>
          <option value="gemini">Gemini</option>
          <option value="ollama">Ollama</option>
        </select>
      </label>
      <label className="form-field">
        Base URL
        <input
          name="baseUrl"
          onChange={(event) => onChange({ ...form, baseUrl: event.target.value })}
          placeholder="Optional"
          type="url"
          value={form.baseUrl}
        />
      </label>
      <label className="form-field">
        Credential plaintext
        <input
          name="credentialPlaintext"
          onChange={(event) => onChange({ ...form, credentialPlaintext: event.target.value })}
          required
          type="password"
          value={form.credentialPlaintext}
        />
      </label>
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Creating..." : "Create provider"}
      </button>
      {provider ? <ResultLine label="Created provider ID" value={provider.id} /> : null}
    </form>
  );
}

function ModelForm({
  form,
  isSubmitting,
  model,
  onChange,
  onSubmit,
}: {
  form: ModelFormState;
  isSubmitting: boolean;
  model?: Model;
  onChange: (form: ModelFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Step 2</p>
      <h2>Add model</h2>
      <label className="form-field">
        Provider ID
        <input
          name="providerId"
          onChange={(event) => onChange({ ...form, providerId: event.target.value })}
          required
          value={form.providerId}
        />
      </label>
      <label className="form-field">
        Model name
        <input
          name="modelName"
          onChange={(event) => onChange({ ...form, modelName: event.target.value })}
          required
          value={form.modelName}
        />
      </label>
      <label className="form-field">
        Display name
        <input
          name="displayName"
          onChange={(event) => onChange({ ...form, displayName: event.target.value })}
          required
          value={form.displayName}
        />
      </label>
      <label className="form-field">
        Model kind
        <select
          name="kind"
          onChange={(event) => onChange({ ...form, kind: event.target.value })}
          required
          value={form.kind}
        >
          <option value="chat">Chat</option>
          <option value="embedding">Embedding</option>
        </select>
      </label>
      <label className="form-field">
        Context window tokens
        <input
          min={1}
          name="contextWindowTokens"
          onChange={(event) => onChange({ ...form, contextWindowTokens: event.target.value })}
          required
          type="number"
          value={form.contextWindowTokens}
        />
      </label>
      <label className="checkbox-field">
        <input
          checked={form.supportsTools}
          name="supportsTools"
          onChange={(event) => onChange({ ...form, supportsTools: event.target.checked })}
          type="checkbox"
        />
        Supports tools
      </label>
      <label className="checkbox-field">
        <input
          checked={form.supportsStructuredOutput}
          name="supportsStructuredOutput"
          onChange={(event) =>
            onChange({ ...form, supportsStructuredOutput: event.target.checked })
          }
          type="checkbox"
        />
        Supports structured output
      </label>
      <label className="checkbox-field">
        <input
          checked={form.supportsVision}
          name="supportsVision"
          onChange={(event) => onChange({ ...form, supportsVision: event.target.checked })}
          type="checkbox"
        />
        Supports vision
      </label>
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Adding..." : "Add model"}
      </button>
      {model ? <ResultLine label="Added model ID" value={model.id} /> : null}
    </form>
  );
}

function PricingForm({
  form,
  isSubmitting,
  model,
  onChange,
  onSubmit,
}: {
  form: PricingFormState;
  isSubmitting: boolean;
  model?: Model;
  onChange: (form: PricingFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Step 3</p>
      <h2>Set pricing</h2>
      <label className="form-field">
        Model ID
        <input
          name="modelId"
          onChange={(event) => onChange({ ...form, modelId: event.target.value })}
          required
          value={form.modelId}
        />
      </label>
      <label className="form-field">
        Price per 1M input tokens
        <input
          min={0}
          name="pricePer1mInputTokens"
          onChange={(event) => onChange({ ...form, pricePer1mInputTokens: event.target.value })}
          step="0.000001"
          type="number"
          value={form.pricePer1mInputTokens}
        />
      </label>
      <label className="form-field">
        Price per 1M output tokens
        <input
          min={0}
          name="pricePer1mOutputTokens"
          onChange={(event) => onChange({ ...form, pricePer1mOutputTokens: event.target.value })}
          step="0.000001"
          type="number"
          value={form.pricePer1mOutputTokens}
        />
      </label>
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Saving..." : "Set pricing"}
      </button>
      {model ? <ResultLine label="Updated model ID" value={model.id} /> : null}
    </form>
  );
}

function ProviderSummary({
  isSubmitting,
  model,
  provider,
}: {
  isSubmitting: boolean;
  model?: Model;
  provider?: Provider;
}) {
  const summaryItems = useMemo(
    () => [
      { label: "Latest provider", value: provider?.name ?? "Not created in this session" },
      { label: "Latest provider ID", value: provider?.id ?? "Not available" },
      { label: "Latest model", value: model?.display_name ?? "Not added in this session" },
      { label: "Latest model ID", value: model?.id ?? "Not available" },
      { label: "Operation status", value: isSubmitting ? "Submitting" : "Ready" },
    ],
    [isSubmitting, model, provider],
  );

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Session summary</p>
          <h2>Recent provider configuration</h2>
        </div>
        <span className="status-pill">Write-only API</span>
      </div>
      <dl className="identity-grid">
        {summaryItems.map((item) => (
          <ResultField key={item.label} label={item.label} value={item.value} />
        ))}
      </dl>
    </section>
  );
}

function ProviderErrorBanner({ error, message }: { error?: Error; message?: string }) {
  const errorMessage =
    error instanceof HifyApiError
      ? `${error.message} (${error.code}, ${error.status})`
      : (message ?? error?.message ?? "Provider operation failed.");

  return (
    <section className="panel panel--danger" role="alert">
      <p className="panel__eyebrow">Provider error</p>
      <h2>Operation failed</h2>
      <p className="muted">{errorMessage}</p>
    </section>
  );
}

function ResultLine({ label, value }: { label: string; value: string }) {
  return (
    <p className="form-result">
      <strong>{label}:</strong> <code>{value}</code>
    </p>
  );
}

function ResultField({ label, value }: { label: string; value: string }) {
  return (
    <div className="identity-field">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function parseRequiredPositiveInteger(value: string, label: string): number {
  const parsedValue = Number(value);

  if (!Number.isInteger(parsedValue) || parsedValue <= 0) {
    throw new Error(`${label} must be a positive integer.`);
  }

  return parsedValue;
}

function parseOptionalNonNegativeNumber(value: string, label: string): number | null {
  const trimmedValue = value.trim();
  if (trimmedValue === "") {
    return null;
  }

  const parsedValue = Number(trimmedValue);
  if (!Number.isFinite(parsedValue) || parsedValue < 0) {
    throw new Error(`${label} must be zero or greater.`);
  }

  return parsedValue;
}
