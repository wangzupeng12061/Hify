"use client";

import { useMemo, useState, type FormEvent } from "react";

import { HifyApiError } from "@/lib/api/errors";

import {
  useCreateWorkflow,
  usePublishWorkflow,
  useUpdateWorkflowDraft,
  useValidateWorkflowDraft,
  useWorkflow,
  useWorkflows,
} from "../hooks";
import type { Workflow, WorkflowValidation, WorkflowVersion } from "../types";

type WorkflowFormState = {
  description: string;
  draftDefinition: string;
  name: string;
};

const defaultWorkflowDefinition = `{
  "nodes": [
    {
      "id": "start",
      "kind": "start",
      "config": {}
    },
    {
      "id": "end",
      "kind": "end",
      "config": {}
    }
  ],
  "edges": [
    {
      "source_node_id": "start",
      "target_node_id": "end"
    }
  ]
}`;

const initialWorkflowForm: WorkflowFormState = {
  description: "",
  draftDefinition: defaultWorkflowDefinition,
  name: "",
};

const EMPTY_WORKFLOWS: Workflow[] = [];

export function WorkflowsManagement() {
  const workflowsQuery = useWorkflows();
  const workflows = workflowsQuery.data ?? EMPTY_WORKFLOWS;
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const effectiveWorkflowId = selectedWorkflowId ?? workflows[0]?.id ?? null;
  const workflowQuery = useWorkflow(
    effectiveWorkflowId === null ? null : { workflowId: effectiveWorkflowId },
  );
  const selectedWorkflow =
    workflowQuery.data ??
    workflows.find((workflow) => workflow.id === effectiveWorkflowId) ??
    workflows[0] ??
    null;

  const createWorkflowMutation = useCreateWorkflow();
  const updateWorkflowDraftMutation = useUpdateWorkflowDraft();
  const validateWorkflowDraftMutation = useValidateWorkflowDraft();
  const publishWorkflowMutation = usePublishWorkflow();

  const [createForm, setCreateForm] = useState(initialWorkflowForm);
  const [draftEditor, setDraftEditor] = useState(defaultWorkflowDefinition);
  const [formError, setFormError] = useState<string | null>(null);

  const workflowSummary = useMemo(() => summarizeWorkflows(workflows), [workflows]);

  async function handleCreateWorkflow(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    try {
      const workflow = await createWorkflowMutation.mutateAsync({
        description: createForm.description.trim() || null,
        draft_definition: parseJsonObject(createForm.draftDefinition, "Initial draft JSON"),
        name: createForm.name.trim(),
      });
      setSelectedWorkflowId(workflow.id);
      setDraftEditor(formatJsonObject(workflow.draft_definition));
      setCreateForm(initialWorkflowForm);
    } catch (error) {
      handleFormError(error, setFormError, "Unable to create workflow.");
    }
  }

  async function handleUpdateDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    if (selectedWorkflow === null) {
      setFormError("Select a workflow before updating its draft.");
      return;
    }

    try {
      const workflow = await updateWorkflowDraftMutation.mutateAsync({
        draft_definition: parseJsonObject(draftEditor, "Draft JSON"),
        workflowId: selectedWorkflow.id,
      });
      setDraftEditor(formatJsonObject(workflow.draft_definition));
    } catch (error) {
      handleFormError(error, setFormError, "Unable to update workflow draft.");
    }
  }

  async function handleValidateDraft() {
    setFormError(null);

    if (selectedWorkflow === null) {
      setFormError("Select a workflow before validating its draft.");
      return;
    }

    try {
      await validateWorkflowDraftMutation.mutateAsync({ workflowId: selectedWorkflow.id });
    } catch (error) {
      handleFormError(error, setFormError, "Unable to validate workflow draft.");
    }
  }

  async function handlePublishWorkflow() {
    setFormError(null);

    if (selectedWorkflow === null) {
      setFormError("Select a workflow before publishing it.");
      return;
    }

    try {
      await publishWorkflowMutation.mutateAsync({ workflowId: selectedWorkflow.id });
    } catch (error) {
      handleFormError(error, setFormError, "Unable to publish workflow.");
    }
  }

  function handleSelectWorkflow(workflow: Workflow) {
    setSelectedWorkflowId(workflow.id);
    setDraftEditor(formatJsonObject(workflow.draft_definition));
    setFormError(null);
  }

  function handleLoadSelectedDraft() {
    if (selectedWorkflow === null) {
      setFormError("Select a workflow before loading its draft.");
      return;
    }

    setDraftEditor(formatJsonObject(selectedWorkflow.draft_definition));
    setFormError(null);
  }

  const operationError =
    workflowsQuery.error ??
    workflowQuery.error ??
    createWorkflowMutation.error ??
    updateWorkflowDraftMutation.error ??
    validateWorkflowDraftMutation.error ??
    publishWorkflowMutation.error;

  return (
    <div className="page-stack">
      <section className="hero">
        <p className="hero__eyebrow">Workflows</p>
        <h2>Manage simplified workflow drafts for agent runs.</h2>
        <p>
          This first version covers the backend workflow contract: create workflow drafts, inspect
          definitions, validate node graphs, and publish immutable workflow versions.
        </p>
      </section>

      {formError ? <WorkflowErrorBanner message={formError} /> : null}
      {operationError ? <WorkflowErrorBanner error={operationError} /> : null}

      <section className="provider-layout">
        <CreateWorkflowForm
          form={createForm}
          isSubmitting={createWorkflowMutation.isPending}
          onChange={setCreateForm}
          onSubmit={handleCreateWorkflow}
        />
        <WorkflowDraftEditor
          draftEditor={draftEditor}
          isPublishing={publishWorkflowMutation.isPending}
          isUpdating={updateWorkflowDraftMutation.isPending}
          isValidating={validateWorkflowDraftMutation.isPending}
          onChange={setDraftEditor}
          onLoadSelectedDraft={handleLoadSelectedDraft}
          onPublish={handlePublishWorkflow}
          onSubmit={handleUpdateDraft}
          onValidate={handleValidateDraft}
          selectedWorkflow={selectedWorkflow}
          validation={validateWorkflowDraftMutation.data}
          workflowVersion={publishWorkflowMutation.data}
        />
      </section>

      <WorkflowCatalog
        isLoading={workflowsQuery.isLoading}
        onSelectWorkflow={handleSelectWorkflow}
        selectedWorkflowId={selectedWorkflow?.id ?? null}
        summary={workflowSummary}
        workflows={workflows}
      />
    </div>
  );
}

function CreateWorkflowForm({
  form,
  isSubmitting,
  onChange,
  onSubmit,
}: {
  form: WorkflowFormState;
  isSubmitting: boolean;
  onChange: (form: WorkflowFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Create workflow</p>
      <h2>New workflow draft</h2>
      <label className="form-field">
        Workflow name
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
        Initial draft JSON
        <textarea
          name="draftDefinition"
          onChange={(event) => onChange({ ...form, draftDefinition: event.target.value })}
          required
          rows={14}
          value={form.draftDefinition}
        />
      </label>
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Creating..." : "Create workflow"}
      </button>
    </form>
  );
}

function WorkflowDraftEditor({
  draftEditor,
  isPublishing,
  isUpdating,
  isValidating,
  onChange,
  onLoadSelectedDraft,
  onPublish,
  onSubmit,
  onValidate,
  selectedWorkflow,
  validation,
  workflowVersion,
}: {
  draftEditor: string;
  isPublishing: boolean;
  isUpdating: boolean;
  isValidating: boolean;
  onChange: (draftEditor: string) => void;
  onLoadSelectedDraft: () => void;
  onPublish: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onValidate: () => void;
  selectedWorkflow: Workflow | null;
  validation?: WorkflowValidation;
  workflowVersion?: WorkflowVersion;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Draft editor</p>
      <h2>{selectedWorkflow === null ? "Select a workflow" : selectedWorkflow.name}</h2>
      {selectedWorkflow === null ? (
        <p className="muted">Create or select a workflow before editing drafts.</p>
      ) : (
        <dl className="identity-grid">
          <ResultField label="Status" value={selectedWorkflow.status} />
          <ResultField
            label="Latest version"
            value={`${selectedWorkflow.latest_version_number}`}
          />
          <ResultField label="Workflow ID" value={selectedWorkflow.id} />
        </dl>
      )}
      <label className="form-field">
        Draft JSON
        <textarea
          name="draftEditor"
          onChange={(event) => onChange(event.target.value)}
          rows={18}
          value={draftEditor}
        />
      </label>
      <div className="button-row">
        <button
          className="button button--secondary"
          disabled={selectedWorkflow === null}
          onClick={onLoadSelectedDraft}
          type="button"
        >
          Load selected draft
        </button>
        <button className="button" disabled={selectedWorkflow === null || isUpdating} type="submit">
          {isUpdating ? "Saving..." : "Save draft"}
        </button>
        <button
          className="button button--secondary"
          disabled={selectedWorkflow === null || isValidating}
          onClick={onValidate}
          type="button"
        >
          {isValidating ? "Validating..." : "Validate"}
        </button>
        <button
          className="button button--secondary"
          disabled={selectedWorkflow === null || isPublishing}
          onClick={onPublish}
          type="button"
        >
          {isPublishing ? "Publishing..." : "Publish"}
        </button>
      </div>
      <WorkflowValidationResult validation={validation} />
      <WorkflowPublishResult workflowVersion={workflowVersion} />
    </form>
  );
}

function WorkflowCatalog({
  isLoading,
  onSelectWorkflow,
  selectedWorkflowId,
  summary,
  workflows,
}: {
  isLoading: boolean;
  onSelectWorkflow: (workflow: Workflow) => void;
  selectedWorkflowId: string | null;
  summary: WorkflowSummary;
  workflows: Workflow[];
}) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Workflow catalog</p>
          <h2>Team workflows</h2>
        </div>
        <span className="status-pill">{isLoading ? "Loading" : `${workflows.length} loaded`}</span>
      </div>
      <dl className="identity-grid">
        <ResultField label="Total workflows" value={`${workflows.length}`} />
        <ResultField label="Draft" value={`${summary.draft}`} />
        <ResultField label="Published" value={`${summary.published}`} />
        <ResultField label="Archived" value={`${summary.archived}`} />
      </dl>
      {isLoading ? <p className="muted">Loading workflows...</p> : null}
      {!isLoading && workflows.length === 0 ? (
        <p className="muted">No workflows yet. Create a draft to populate the catalog.</p>
      ) : null}
      {workflows.length > 0 ? (
        <ul className="timeline-list">
          {workflows.map((workflow) => {
            const definitionSummary = summarizeDefinition(workflow.draft_definition);
            const isSelected = workflow.id === selectedWorkflowId;

            return (
              <li className="timeline-list__item" key={workflow.id}>
                <span>{`${workflow.status} · v${workflow.latest_version_number}`}</span>
                <p>{workflow.name}</p>
                <p className="muted">{workflow.description ?? "No description"}</p>
                <p className="form-result">
                  <strong>Draft graph:</strong> {definitionSummary}
                </p>
                <p className="form-result">
                  <strong>Workflow ID:</strong> <code>{workflow.id}</code>
                </p>
                <button
                  className="button button--secondary"
                  onClick={() => onSelectWorkflow(workflow)}
                  type="button"
                >
                  {isSelected ? "Selected" : "Edit draft"}
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}

function WorkflowValidationResult({ validation }: { validation?: WorkflowValidation }) {
  if (validation === undefined) {
    return null;
  }

  if (validation.is_valid) {
    return (
      <section className="panel panel--success">
        <p className="panel__eyebrow">Validation</p>
        <h2>Workflow draft is valid</h2>
        <p className="muted">The current backend draft passed static workflow validation.</p>
      </section>
    );
  }

  return (
    <section className="panel panel--danger">
      <p className="panel__eyebrow">Validation</p>
      <h2>Workflow draft has issues</h2>
      <ul className="timeline-list">
        {validation.issues.map((issue) => (
          <li className="timeline-list__item" key={`${issue.code}-${issue.path}`}>
            <span>{issue.code}</span>
            <p>{issue.path}</p>
            <p className="muted">{issue.message}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function WorkflowPublishResult({ workflowVersion }: { workflowVersion?: WorkflowVersion }) {
  if (workflowVersion === undefined) {
    return null;
  }

  return (
    <section className="panel panel--success">
      <p className="panel__eyebrow">Published version</p>
      <h2>{`Published v${workflowVersion.version_number}`}</h2>
      <p className="muted">{workflowVersion.name}</p>
      <p className="form-result">
        <strong>Version ID:</strong> <code>{workflowVersion.id}</code>
      </p>
    </section>
  );
}

function ResultField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function WorkflowErrorBanner({ error, message }: { error?: Error; message?: string }) {
  const errorMessage =
    error instanceof HifyApiError
      ? `${error.message} (${error.code}, ${error.status})`
      : (message ?? error?.message ?? "Workflow operation failed.");

  return (
    <section className="panel panel--danger" role="alert">
      <p className="panel__eyebrow">Workflow error</p>
      <h2>Operation failed</h2>
      <p className="muted">{errorMessage}</p>
    </section>
  );
}

type WorkflowSummary = {
  archived: number;
  draft: number;
  published: number;
};

function summarizeWorkflows(workflows: Workflow[]): WorkflowSummary {
  return workflows.reduce<WorkflowSummary>(
    (summary, workflow) => {
      if (workflow.status === "published") {
        return { ...summary, published: summary.published + 1 };
      }
      if (workflow.status === "archived") {
        return { ...summary, archived: summary.archived + 1 };
      }
      return { ...summary, draft: summary.draft + 1 };
    },
    { archived: 0, draft: 0, published: 0 },
  );
}

function summarizeDefinition(definition: Record<string, unknown>): string {
  const nodes = Array.isArray(definition.nodes) ? definition.nodes.length : 0;
  const edges = Array.isArray(definition.edges) ? definition.edges.length : 0;
  return `${nodes} nodes / ${edges} edges`;
}

function parseJsonObject(value: string, label: string): Record<string, unknown> {
  let parsed: unknown;

  try {
    parsed = JSON.parse(value);
  } catch (error) {
    throw new Error(`${label} must be valid JSON.`, { cause: error });
  }

  if (!isPlainObject(parsed)) {
    throw new Error(`${label} must be a JSON object.`);
  }

  return parsed;
}

function formatJsonObject(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function handleFormError(
  error: unknown,
  setFormError: (message: string) => void,
  fallbackMessage: string,
) {
  if (error instanceof Error) {
    setFormError(error.message);
    return;
  }

  setFormError(fallbackMessage);
}
