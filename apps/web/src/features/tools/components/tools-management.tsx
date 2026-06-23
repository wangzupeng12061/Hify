"use client";

import { useMemo, useState, type FormEvent } from "react";

import { HifyApiError } from "@/lib/api/errors";

import { useCreateTool, useTools } from "../hooks";
import type { Tool } from "../types";

type HttpToolFormState = {
  description: string;
  endpointUrl: string;
  httpHeaders: string;
  httpMethod: string;
  inputSchema: string;
  name: string;
};

type BuiltinToolFormState = {
  builtinName: string;
  description: string;
  inputSchema: string;
  name: string;
};

const defaultInputSchema = `{
  "type": "object",
  "properties": {},
  "required": []
}`;

const defaultHttpHeaders = "{}";

const initialHttpToolForm: HttpToolFormState = {
  description: "",
  endpointUrl: "",
  httpHeaders: defaultHttpHeaders,
  httpMethod: "POST",
  inputSchema: defaultInputSchema,
  name: "",
};

const initialBuiltinToolForm: BuiltinToolFormState = {
  builtinName: "",
  description: "",
  inputSchema: defaultInputSchema,
  name: "",
};

const EMPTY_TOOLS: Tool[] = [];

export function ToolsManagement() {
  const toolsQuery = useTools();
  const createToolMutation = useCreateTool();
  const [httpToolForm, setHttpToolForm] = useState(initialHttpToolForm);
  const [builtinToolForm, setBuiltinToolForm] = useState(initialBuiltinToolForm);
  const [formError, setFormError] = useState<string | null>(null);

  const tools = toolsQuery.data ?? EMPTY_TOOLS;
  const groupedCounts = useMemo(() => countToolsByKind(tools), [tools]);

  async function handleCreateHttpTool(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    try {
      await createToolMutation.mutateAsync({
        builtin_name: null,
        description: httpToolForm.description.trim() || null,
        endpoint_url: httpToolForm.endpointUrl.trim(),
        http_headers: parseStringRecord(httpToolForm.httpHeaders, "HTTP headers"),
        http_method: httpToolForm.httpMethod,
        input_schema: parseObjectSchema(httpToolForm.inputSchema),
        mcp_server_id: null,
        mcp_tool_id: null,
        mcp_tool_name: null,
        name: httpToolForm.name.trim(),
        tool_kind: "http",
      });
      setHttpToolForm(initialHttpToolForm);
    } catch (error) {
      handleFormError(error, setFormError, "Unable to create HTTP tool.");
    }
  }

  async function handleCreateBuiltinTool(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    try {
      await createToolMutation.mutateAsync({
        builtin_name: builtinToolForm.builtinName.trim(),
        description: builtinToolForm.description.trim() || null,
        endpoint_url: null,
        http_headers: {},
        http_method: null,
        input_schema: parseObjectSchema(builtinToolForm.inputSchema),
        mcp_server_id: null,
        mcp_tool_id: null,
        mcp_tool_name: null,
        name: builtinToolForm.name.trim(),
        tool_kind: "builtin",
      });
      setBuiltinToolForm(initialBuiltinToolForm);
    } catch (error) {
      handleFormError(error, setFormError, "Unable to create builtin tool.");
    }
  }

  const operationError = toolsQuery.error ?? createToolMutation.error;

  return (
    <div className="page-stack">
      <section className="hero">
        <p className="hero__eyebrow">Tools</p>
        <h2>Manage tools that agents can call during runs.</h2>
        <p>
          This first version exposes the backend tool catalog: create HTTP and builtin tools,
          inspect available tools, and keep MCP-adapted tools visible as catalog entries.
        </p>
      </section>

      {formError ? <ToolErrorBanner message={formError} /> : null}
      {operationError ? <ToolErrorBanner error={operationError} /> : null}

      <section className="provider-layout">
        <CreateHttpToolForm
          form={httpToolForm}
          isSubmitting={createToolMutation.isPending}
          onChange={setHttpToolForm}
          onSubmit={handleCreateHttpTool}
        />
        <CreateBuiltinToolForm
          form={builtinToolForm}
          isSubmitting={createToolMutation.isPending}
          onChange={setBuiltinToolForm}
          onSubmit={handleCreateBuiltinTool}
        />
      </section>

      <ToolCatalogSummary
        groupedCounts={groupedCounts}
        isLoading={toolsQuery.isLoading}
        tools={tools}
      />
    </div>
  );
}

function CreateHttpToolForm({
  form,
  isSubmitting,
  onChange,
  onSubmit,
}: {
  form: HttpToolFormState;
  isSubmitting: boolean;
  onChange: (form: HttpToolFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">HTTP tool</p>
      <h2>Create HTTP tool</h2>
      <label className="form-field">
        Tool name
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
        Endpoint URL
        <input
          name="endpointUrl"
          onChange={(event) => onChange({ ...form, endpointUrl: event.target.value })}
          required
          value={form.endpointUrl}
        />
      </label>
      <label className="form-field">
        HTTP method
        <select
          name="httpMethod"
          onChange={(event) => onChange({ ...form, httpMethod: event.target.value })}
          required
          value={form.httpMethod}
        >
          {["GET", "POST", "PUT", "PATCH", "DELETE"].map((method) => (
            <option key={method} value={method}>
              {method}
            </option>
          ))}
        </select>
      </label>
      <label className="form-field">
        HTTP headers JSON
        <textarea
          name="httpHeaders"
          onChange={(event) => onChange({ ...form, httpHeaders: event.target.value })}
          rows={5}
          value={form.httpHeaders}
        />
      </label>
      <label className="form-field">
        Input schema JSON
        <textarea
          name="inputSchema"
          onChange={(event) => onChange({ ...form, inputSchema: event.target.value })}
          required
          rows={8}
          value={form.inputSchema}
        />
      </label>
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Creating..." : "Create HTTP tool"}
      </button>
    </form>
  );
}

function CreateBuiltinToolForm({
  form,
  isSubmitting,
  onChange,
  onSubmit,
}: {
  form: BuiltinToolFormState;
  isSubmitting: boolean;
  onChange: (form: BuiltinToolFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Builtin tool</p>
      <h2>Create builtin tool</h2>
      <label className="form-field">
        Tool name
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
        Builtin name
        <input
          name="builtinName"
          onChange={(event) => onChange({ ...form, builtinName: event.target.value })}
          placeholder="Example: web.search"
          required
          value={form.builtinName}
        />
      </label>
      <label className="form-field">
        Input schema JSON
        <textarea
          name="inputSchema"
          onChange={(event) => onChange({ ...form, inputSchema: event.target.value })}
          required
          rows={8}
          value={form.inputSchema}
        />
      </label>
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Creating..." : "Create builtin tool"}
      </button>
    </form>
  );
}

function ToolCatalogSummary({
  groupedCounts,
  isLoading,
  tools,
}: {
  groupedCounts: Record<string, number>;
  isLoading: boolean;
  tools: Tool[];
}) {
  const summaryItems = [
    { label: "Total tools", value: `${tools.length}` },
    { label: "HTTP tools", value: `${groupedCounts.http ?? 0}` },
    { label: "Builtin tools", value: `${groupedCounts.builtin ?? 0}` },
    { label: "MCP tools", value: `${groupedCounts.mcp ?? 0}` },
  ];

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Tool catalog</p>
          <h2>Available tools</h2>
        </div>
        <span className="status-pill">{isLoading ? "Loading" : `${tools.length} loaded`}</span>
      </div>
      <dl className="identity-grid">
        {summaryItems.map((item) => (
          <ResultField key={item.label} label={item.label} value={item.value} />
        ))}
      </dl>
      {isLoading ? <p className="muted">Loading tools...</p> : null}
      {!isLoading && tools.length === 0 ? (
        <p className="muted">No tools yet. Create an HTTP or builtin tool to populate the catalog.</p>
      ) : null}
      {tools.length > 0 ? (
        <ul className="timeline-list">
          {tools.map((tool) => (
            <li className="timeline-list__item" key={tool.id}>
              <span>{`${tool.tool_kind} · ${tool.status}`}</span>
              <p>{tool.name}</p>
              <p className="muted">{tool.description ?? "No description"}</p>
              <p className="form-result">
                <strong>Tool ID:</strong> <code>{tool.id}</code>
              </p>
              <p className="form-result">
                <strong>Target:</strong> {formatToolTarget(tool)}
              </p>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function ToolErrorBanner({ error, message }: { error?: Error; message?: string }) {
  const errorMessage =
    error instanceof HifyApiError
      ? `${error.message} (${error.code}, ${error.status})`
      : (message ?? error?.message ?? "Tool operation failed.");

  return (
    <section className="panel panel--danger" role="alert">
      <p className="panel__eyebrow">Tool error</p>
      <h2>Operation failed</h2>
      <p className="muted">{errorMessage}</p>
    </section>
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

function countToolsByKind(tools: Tool[]): Record<string, number> {
  return tools.reduce<Record<string, number>>((counts, tool) => {
    counts[tool.tool_kind] = (counts[tool.tool_kind] ?? 0) + 1;
    return counts;
  }, {});
}

function formatToolTarget(tool: Tool): string {
  if (tool.tool_kind === "http") {
    return `${tool.http_method ?? "HTTP"} ${tool.endpoint_url ?? "No endpoint"}`;
  }

  if (tool.tool_kind === "builtin") {
    return tool.builtin_name ?? "No builtin name";
  }

  if (tool.tool_kind === "mcp") {
    return tool.mcp_tool_name ?? tool.mcp_tool_id ?? "MCP tool";
  }

  return "Unknown target";
}

function parseObjectSchema(value: string): Record<string, unknown> {
  const parsedValue = parseJsonObject(value, "Input schema");
  return parsedValue;
}

function parseStringRecord(value: string, label: string): Record<string, string> {
  const parsedValue = parseJsonObject(value, label);
  const entries = Object.entries(parsedValue);
  const invalidEntry = entries.find(([, entryValue]) => typeof entryValue !== "string");
  if (invalidEntry !== undefined) {
    throw new Error(`${label} must be a JSON object with string values.`);
  }

  return Object.fromEntries(entries) as Record<string, string>;
}

function parseJsonObject(value: string, label: string): Record<string, unknown> {
  let parsedValue: unknown;
  try {
    parsedValue = JSON.parse(value);
  } catch (error) {
    throw new Error(`${label} must be valid JSON.`, { cause: error });
  }

  if (!isPlainObject(parsedValue)) {
    throw new Error(`${label} must be a JSON object.`);
  }

  return parsedValue;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function handleFormError(
  error: unknown,
  setFormError: (message: string | null) => void,
  fallbackMessage: string,
) {
  if (!(error instanceof HifyApiError)) {
    setFormError(error instanceof Error ? error.message : fallbackMessage);
  }
}
