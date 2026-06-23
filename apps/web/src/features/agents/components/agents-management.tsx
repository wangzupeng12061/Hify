"use client";

import { useMemo, useState, type FormEvent } from "react";

import { HifyApiError } from "@/lib/api/errors";

import { useCreateAgent, usePublishAgent } from "../hooks";
import type { Agent, AgentVersion } from "../types";

type AgentFormState = {
  description: string;
  knowledgeBaseIds: string;
  name: string;
  providerModelId: string;
  systemPrompt: string;
  workflowId: string;
};

type PublishFormState = {
  agentId: string;
};

const initialAgentForm: AgentFormState = {
  description: "",
  knowledgeBaseIds: "",
  name: "",
  providerModelId: "",
  systemPrompt: "You are a helpful internal team assistant.",
  workflowId: "",
};

const initialPublishForm: PublishFormState = {
  agentId: "",
};

export function AgentsManagement() {
  const createAgentMutation = useCreateAgent();
  const publishAgentMutation = usePublishAgent();
  const [agentForm, setAgentForm] = useState(initialAgentForm);
  const [publishForm, setPublishForm] = useState(initialPublishForm);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleCreateAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    try {
      await createAgentMutation.mutateAsync({
        description: agentForm.description.trim() || null,
        knowledge_base_ids: parseCommaSeparatedIds(agentForm.knowledgeBaseIds),
        name: agentForm.name.trim(),
        provider_model_id: agentForm.providerModelId.trim(),
        system_prompt: agentForm.systemPrompt.trim(),
        workflow_id: agentForm.workflowId.trim() || null,
      });
    } catch (error) {
      if (!(error instanceof HifyApiError)) {
        setFormError(error instanceof Error ? error.message : "Unable to create agent.");
      }
    }
  }

  async function handlePublishAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    try {
      await publishAgentMutation.mutateAsync({
        agentId: publishForm.agentId.trim(),
      });
    } catch {
      return;
    }
  }

  const operationError = createAgentMutation.error ?? publishAgentMutation.error;
  const isSubmitting = createAgentMutation.isPending || publishAgentMutation.isPending;

  return (
    <div className="page-stack">
      <section className="hero">
        <p className="hero__eyebrow">Agents</p>
        <h2>Configure an agent and publish a runnable version.</h2>
        <p>
          This first version matches the backend contract: create an agent from a model, prompt,
          optional knowledge bases, and optional workflow, then publish it by Agent ID.
        </p>
      </section>

      {formError ? <AgentErrorBanner message={formError} /> : null}
      {operationError ? <AgentErrorBanner error={operationError} /> : null}

      <section className="provider-layout">
        <CreateAgentForm
          agent={createAgentMutation.data}
          form={agentForm}
          isSubmitting={createAgentMutation.isPending}
          onChange={setAgentForm}
          onSubmit={handleCreateAgent}
        />
        <PublishAgentForm
          form={publishForm}
          isSubmitting={publishAgentMutation.isPending}
          onChange={setPublishForm}
          onSubmit={handlePublishAgent}
          version={publishAgentMutation.data}
        />
      </section>

      <AgentSummary
        agent={createAgentMutation.data}
        isSubmitting={isSubmitting}
        version={publishAgentMutation.data}
      />
    </div>
  );
}

function CreateAgentForm({
  agent,
  form,
  isSubmitting,
  onChange,
  onSubmit,
}: {
  agent?: Agent;
  form: AgentFormState;
  isSubmitting: boolean;
  onChange: (form: AgentFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Step 1</p>
      <h2>Create agent</h2>
      <label className="form-field">
        Agent name
        <input
          name="name"
          onChange={(event) => onChange({ ...form, name: event.target.value })}
          required
          value={form.name}
        />
      </label>
      <label className="form-field">
        Description
        <input
          name="description"
          onChange={(event) => onChange({ ...form, description: event.target.value })}
          placeholder="Optional"
          value={form.description}
        />
      </label>
      <label className="form-field">
        Provider model ID
        <input
          name="providerModelId"
          onChange={(event) => onChange({ ...form, providerModelId: event.target.value })}
          required
          value={form.providerModelId}
        />
      </label>
      <label className="form-field">
        Knowledge base IDs
        <input
          name="knowledgeBaseIds"
          onChange={(event) => onChange({ ...form, knowledgeBaseIds: event.target.value })}
          placeholder="Optional, comma-separated"
          value={form.knowledgeBaseIds}
        />
      </label>
      <label className="form-field">
        Workflow ID
        <input
          name="workflowId"
          onChange={(event) => onChange({ ...form, workflowId: event.target.value })}
          placeholder="Optional"
          value={form.workflowId}
        />
      </label>
      <label className="form-field">
        System prompt
        <textarea
          name="systemPrompt"
          onChange={(event) => onChange({ ...form, systemPrompt: event.target.value })}
          required
          rows={7}
          value={form.systemPrompt}
        />
      </label>
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Creating..." : "Create agent"}
      </button>
      {agent ? <ResultLine label="Created agent ID" value={agent.id} /> : null}
    </form>
  );
}

function PublishAgentForm({
  form,
  isSubmitting,
  onChange,
  onSubmit,
  version,
}: {
  form: PublishFormState;
  isSubmitting: boolean;
  onChange: (form: PublishFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  version?: AgentVersion;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Step 2</p>
      <h2>Publish version</h2>
      <p className="muted">
        Publish freezes the current agent configuration into a version that Runs can execute.
      </p>
      <label className="form-field">
        Agent ID
        <input
          name="agentId"
          onChange={(event) => onChange({ agentId: event.target.value })}
          required
          value={form.agentId}
        />
      </label>
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Publishing..." : "Publish agent"}
      </button>
      {version ? (
        <ResultLine label="Published version" value={`${version.version_number}`} />
      ) : null}
    </form>
  );
}

function AgentSummary({
  agent,
  isSubmitting,
  version,
}: {
  agent?: Agent;
  isSubmitting: boolean;
  version?: AgentVersion;
}) {
  const summaryItems = useMemo(
    () => [
      { label: "Latest agent", value: agent?.name ?? "Not created in this session" },
      { label: "Latest agent ID", value: agent?.id ?? "Not available" },
      { label: "Provider model ID", value: agent?.provider_model_id ?? "Not available" },
      { label: "Latest version", value: version ? `${version.version_number}` : "Not published" },
      { label: "Operation status", value: isSubmitting ? "Submitting" : "Ready" },
    ],
    [agent, isSubmitting, version],
  );

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Session summary</p>
          <h2>Recent agent configuration</h2>
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

function AgentErrorBanner({ error, message }: { error?: Error; message?: string }) {
  const errorMessage =
    error instanceof HifyApiError
      ? `${error.message} (${error.code}, ${error.status})`
      : (message ?? error?.message ?? "Agent operation failed.");

  return (
    <section className="panel panel--danger" role="alert">
      <p className="panel__eyebrow">Agent error</p>
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

function parseCommaSeparatedIds(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}
