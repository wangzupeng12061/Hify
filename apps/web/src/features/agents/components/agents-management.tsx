"use client";

import { useMemo, useState, type FormEvent } from "react";

import { useKnowledgeBases, type KnowledgeBase } from "@/features/knowledge";
import { useProviderModels, type Model } from "@/features/providers";
import { useWorkflows, type Workflow } from "@/features/workflows";
import { HifyApiError } from "@/lib/api/errors";

import { useCreateAgent, usePublishAgent } from "../hooks";
import type { Agent, AgentVersion } from "../types";

type AgentFormState = {
  description: string;
  knowledgeBaseIds: string[];
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
  knowledgeBaseIds: [],
  name: "",
  providerModelId: "",
  systemPrompt: "You are a helpful internal team assistant.",
  workflowId: "",
};

const initialPublishForm: PublishFormState = {
  agentId: "",
};

const EMPTY_KNOWLEDGE_BASES: KnowledgeBase[] = [];
const EMPTY_PROVIDER_MODELS: Model[] = [];
const EMPTY_WORKFLOWS: Workflow[] = [];

export function AgentsManagement() {
  const createAgentMutation = useCreateAgent();
  const publishAgentMutation = usePublishAgent();
  const knowledgeBasesQuery = useKnowledgeBases();
  const providerModelsQuery = useProviderModels();
  const workflowsQuery = useWorkflows();
  const [agentForm, setAgentForm] = useState(initialAgentForm);
  const [publishForm, setPublishForm] = useState(initialPublishForm);
  const [formError, setFormError] = useState<string | null>(null);
  const knowledgeBases = knowledgeBasesQuery.data ?? EMPTY_KNOWLEDGE_BASES;
  const providerModels = providerModelsQuery.data ?? EMPTY_PROVIDER_MODELS;
  const activeChatModels = useMemo(() => getActiveChatModels(providerModels), [providerModels]);
  const activeKnowledgeBases = useMemo(
    () => getActiveKnowledgeBases(knowledgeBases),
    [knowledgeBases],
  );
  const workflows = workflowsQuery.data ?? EMPTY_WORKFLOWS;
  const publishedWorkflows = useMemo(() => getPublishedWorkflows(workflows), [workflows]);
  const selectedModel =
    activeChatModels.find((model) => model.id === agentForm.providerModelId) ?? null;
  const selectedKnowledgeBases = activeKnowledgeBases.filter((knowledgeBase) =>
    agentForm.knowledgeBaseIds.includes(knowledgeBase.id),
  );
  const selectedWorkflow =
    publishedWorkflows.find((workflow) => workflow.id === agentForm.workflowId) ?? null;

  async function handleCreateAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    try {
      const agent = await createAgentMutation.mutateAsync({
        description: agentForm.description.trim() || null,
        knowledge_base_ids: agentForm.knowledgeBaseIds,
        name: agentForm.name.trim(),
        provider_model_id: agentForm.providerModelId.trim(),
        system_prompt: agentForm.systemPrompt.trim(),
        workflow_id: agentForm.workflowId.trim() || null,
      });
      setPublishForm({ agentId: agent.id });
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

  const operationError =
    providerModelsQuery.error ??
    knowledgeBasesQuery.error ??
    workflowsQuery.error ??
    createAgentMutation.error ??
    publishAgentMutation.error;
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
          activeKnowledgeBases={activeKnowledgeBases}
          activeChatModels={activeChatModels}
          form={agentForm}
          isSubmitting={createAgentMutation.isPending}
          knowledgeBasesLoading={knowledgeBasesQuery.isLoading}
          onChange={setAgentForm}
          onSubmit={handleCreateAgent}
          publishedWorkflows={publishedWorkflows}
          selectedKnowledgeBases={selectedKnowledgeBases}
          selectedModel={selectedModel}
          selectedWorkflow={selectedWorkflow}
          providerModelsLoading={providerModelsQuery.isLoading}
          workflowsLoading={workflowsQuery.isLoading}
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
        selectedKnowledgeBases={selectedKnowledgeBases}
        selectedModel={selectedModel}
        selectedWorkflow={selectedWorkflow}
        version={publishAgentMutation.data}
      />
    </div>
  );
}

function CreateAgentForm({
  agent,
  activeKnowledgeBases,
  activeChatModels,
  form,
  isSubmitting,
  knowledgeBasesLoading,
  onChange,
  onSubmit,
  publishedWorkflows,
  selectedKnowledgeBases,
  selectedModel,
  selectedWorkflow,
  providerModelsLoading,
  workflowsLoading,
}: {
  agent?: Agent;
  activeKnowledgeBases: KnowledgeBase[];
  activeChatModels: Model[];
  form: AgentFormState;
  isSubmitting: boolean;
  knowledgeBasesLoading: boolean;
  onChange: (form: AgentFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  publishedWorkflows: Workflow[];
  selectedKnowledgeBases: KnowledgeBase[];
  selectedModel: Model | null;
  selectedWorkflow: Workflow | null;
  providerModelsLoading: boolean;
  workflowsLoading: boolean;
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
        Provider model
        <select
          name="providerModelId"
          onChange={(event) => onChange({ ...form, providerModelId: event.target.value })}
          required
          value={form.providerModelId}
        >
          <option value="">Select a chat model</option>
          {activeChatModels.map((model) => (
            <option key={model.id} value={model.id}>
              {formatModelOption(model)}
            </option>
          ))}
        </select>
      </label>
      {providerModelsLoading ? <p className="muted">Loading provider models...</p> : null}
      {!providerModelsLoading && activeChatModels.length === 0 ? (
        <p className="muted">No active chat models are available. Add one in Providers first.</p>
      ) : null}
      {selectedModel ? <ResultLine label="Selected model ID" value={selectedModel.id} /> : null}
      <fieldset className="form-field">
        <legend>Knowledge bases</legend>
        {activeKnowledgeBases.map((knowledgeBase) => (
          <label key={knowledgeBase.id}>
            <input
              checked={form.knowledgeBaseIds.includes(knowledgeBase.id)}
              name="knowledgeBaseIds"
              onChange={(event) =>
                onChange({
                  ...form,
                  knowledgeBaseIds: toggleId(
                    form.knowledgeBaseIds,
                    knowledgeBase.id,
                    event.target.checked,
                  ),
                })
              }
              type="checkbox"
              value={knowledgeBase.id}
            />{" "}
            {knowledgeBase.name}
          </label>
        ))}
      </fieldset>
      {knowledgeBasesLoading ? <p className="muted">Loading knowledge bases...</p> : null}
      {!knowledgeBasesLoading && activeKnowledgeBases.length === 0 ? (
        <p className="muted">No active knowledge bases are available. This agent can run without RAG.</p>
      ) : null}
      {selectedKnowledgeBases.length > 0 ? (
        <ResultLine
          label="Selected knowledge bases"
          value={selectedKnowledgeBases.map((knowledgeBase) => knowledgeBase.name).join(", ")}
        />
      ) : null}
      <label className="form-field">
        Workflow
        <select
          name="workflowId"
          onChange={(event) => onChange({ ...form, workflowId: event.target.value })}
          value={form.workflowId}
        >
          <option value="">No workflow binding</option>
          {publishedWorkflows.map((workflow) => (
            <option key={workflow.id} value={workflow.id}>
              {formatWorkflowOption(workflow)}
            </option>
          ))}
        </select>
      </label>
      {workflowsLoading ? <p className="muted">Loading published workflows...</p> : null}
      {!workflowsLoading && publishedWorkflows.length === 0 ? (
        <p className="muted">
          No published workflows are available. Create and publish a workflow first to bind it.
        </p>
      ) : null}
      {selectedWorkflow ? (
        <ResultLine label="Selected workflow ID" value={selectedWorkflow.id} />
      ) : null}
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
  selectedKnowledgeBases,
  selectedModel,
  selectedWorkflow,
  version,
}: {
  agent?: Agent;
  isSubmitting: boolean;
  selectedKnowledgeBases: KnowledgeBase[];
  selectedModel: Model | null;
  selectedWorkflow: Workflow | null;
  version?: AgentVersion;
}) {
  const summaryItems = useMemo(
    () => [
      { label: "Latest agent", value: agent?.name ?? "Not created in this session" },
      { label: "Latest agent ID", value: agent?.id ?? "Not available" },
      {
        label: "Provider model",
        value:
          selectedModel?.display_name ??
          (agent?.provider_model_id ? `Model ${agent.provider_model_id}` : "Not available"),
      },
      {
        label: "Knowledge bases",
        value:
          selectedKnowledgeBases.length > 0
            ? selectedKnowledgeBases.map((knowledgeBase) => knowledgeBase.name).join(", ")
            : "No RAG binding",
      },
      {
        label: "Configured workflow",
        value:
          selectedWorkflow?.name ??
          (agent?.workflow_id ? `Workflow ${agent.workflow_id}` : "No workflow binding"),
      },
      {
        label: "Published workflow",
        value:
          version?.workflow_name && version.workflow_version_number
            ? `${version.workflow_name} v${version.workflow_version_number}`
            : "Not published with workflow",
      },
      { label: "Latest version", value: version ? `${version.version_number}` : "Not published" },
      { label: "Operation status", value: isSubmitting ? "Submitting" : "Ready" },
    ],
    [agent, isSubmitting, selectedKnowledgeBases, selectedModel, selectedWorkflow, version],
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

function getPublishedWorkflows(workflows: Workflow[]): Workflow[] {
  return workflows.filter(
    (workflow) => workflow.status === "published" && workflow.latest_version_number > 0,
  );
}

function getActiveChatModels(models: Model[]): Model[] {
  return models.filter((model) => model.kind === "chat" && model.status === "active");
}

function getActiveKnowledgeBases(knowledgeBases: KnowledgeBase[]): KnowledgeBase[] {
  return knowledgeBases.filter((knowledgeBase) => knowledgeBase.status === "active");
}

function toggleId(ids: string[], id: string, isSelected: boolean): string[] {
  if (isSelected) {
    return ids.includes(id) ? ids : [...ids, id];
  }

  return ids.filter((currentId) => currentId !== id);
}

function formatModelOption(model: Model): string {
  return `${model.provider_name} · ${model.display_name}`;
}

function formatWorkflowOption(workflow: Workflow): string {
  return `${workflow.name} · v${workflow.latest_version_number}`;
}
