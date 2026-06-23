"use client";

import { useMemo, useState, type FormEvent } from "react";

import { HifyApiError } from "@/lib/api/errors";

import {
  useCreateMcpServer,
  useMcpServers,
  useMcpTools,
  useRefreshMcpTools,
} from "../hooks";
import type { McpServer, McpTool } from "../types";

type McpServerFormState = {
  description: string;
  endpointUrl: string;
  name: string;
  transport: string;
};

const initialMcpServerForm: McpServerFormState = {
  description: "",
  endpointUrl: "",
  name: "",
  transport: "streamable_http",
};

const EMPTY_SERVERS: McpServer[] = [];
const EMPTY_TOOLS: McpTool[] = [];

export function McpManagement() {
  const serversQuery = useMcpServers();
  const createServerMutation = useCreateMcpServer();
  const refreshToolsMutation = useRefreshMcpTools();
  const [serverForm, setServerForm] = useState(initialMcpServerForm);
  const [selectedServerId, setSelectedServerId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const servers = serversQuery.data ?? EMPTY_SERVERS;
  const effectiveServerId = useMemo(() => {
    if (servers.some((server) => server.id === selectedServerId)) {
      return selectedServerId;
    }

    return servers[0]?.id ?? "";
  }, [selectedServerId, servers]);
  const selectedServer = useMemo(
    () => servers.find((server) => server.id === effectiveServerId),
    [effectiveServerId, servers],
  );
  const toolsQuery = useMcpTools(
    effectiveServerId === ""
      ? null
      : {
          serverId: effectiveServerId,
        },
  );
  const tools = toolsQuery.data ?? EMPTY_TOOLS;

  async function handleCreateServer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    try {
      const server = await createServerMutation.mutateAsync({
        description: serverForm.description.trim() || null,
        endpoint_url: serverForm.endpointUrl.trim(),
        name: serverForm.name.trim(),
        transport: serverForm.transport,
      });
      setSelectedServerId(server.id);
      setServerForm(initialMcpServerForm);
    } catch (error) {
      handleFormError(error, setFormError, "Unable to create MCP server.");
    }
  }

  async function handleRefreshTools() {
    setFormError(null);

    if (effectiveServerId === "") {
      setFormError("Select or create an MCP server before refreshing tools.");
      return;
    }

    try {
      await refreshToolsMutation.mutateAsync({
        serverId: effectiveServerId,
      });
    } catch (error) {
      handleFormError(error, setFormError, "Unable to refresh MCP tools.");
    }
  }

  const operationError =
    serversQuery.error ?? toolsQuery.error ?? createServerMutation.error ?? refreshToolsMutation.error;
  const isUpdating = createServerMutation.isPending || refreshToolsMutation.isPending;

  return (
    <div className="page-stack">
      <section className="hero">
        <p className="hero__eyebrow">MCP</p>
        <h2>Manage MCP servers and discovered tools.</h2>
        <p>
          This first version configures streamable HTTP MCP servers, lists discovered MCP tools,
          and lets operators refresh discovery so tools can flow into the Hify tool catalog.
        </p>
      </section>

      {formError ? <McpErrorBanner message={formError} /> : null}
      {operationError ? <McpErrorBanner error={operationError} /> : null}

      <section className="provider-layout">
        <CreateMcpServerForm
          form={serverForm}
          isSubmitting={createServerMutation.isPending}
          onChange={setServerForm}
          onSubmit={handleCreateServer}
        />
        <McpServerDetails
          isRefreshing={refreshToolsMutation.isPending}
          onRefresh={handleRefreshTools}
          selectedServer={selectedServer}
          tools={tools}
        />
      </section>

      <McpServersPanel
        isLoading={serversQuery.isLoading}
        isUpdating={isUpdating}
        onSelect={setSelectedServerId}
        selectedServerId={effectiveServerId}
        servers={servers}
      />

      <McpToolsPanel
        isLoading={toolsQuery.isLoading}
        selectedServer={selectedServer}
        tools={tools}
      />
    </div>
  );
}

function CreateMcpServerForm({
  form,
  isSubmitting,
  onChange,
  onSubmit,
}: {
  form: McpServerFormState;
  isSubmitting: boolean;
  onChange: (form: McpServerFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Server</p>
      <h2>Create MCP server</h2>
      <label className="form-field">
        Server name
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
        Transport
        <select
          name="transport"
          onChange={(event) => onChange({ ...form, transport: event.target.value })}
          required
          value={form.transport}
        >
          <option value="streamable_http">streamable_http</option>
        </select>
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
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Creating..." : "Create MCP server"}
      </button>
    </form>
  );
}

function McpServerDetails({
  isRefreshing,
  onRefresh,
  selectedServer,
  tools,
}: {
  isRefreshing: boolean;
  onRefresh: () => void;
  selectedServer?: McpServer;
  tools: McpTool[];
}) {
  const detailItems = [
    { label: "Selected server", value: selectedServer?.name ?? "Not selected" },
    { label: "Server ID", value: selectedServer?.id ?? "Not available" },
    { label: "Status", value: selectedServer?.status ?? "Not available" },
    { label: "Discovered tools", value: `${tools.length}` },
  ];

  return (
    <section className="panel form-panel">
      <p className="panel__eyebrow">Discovery</p>
      <h2>Refresh MCP tools</h2>
      <p className="muted">
        Refresh discovery reads the selected MCP server and updates the Hify MCP tool list.
      </p>
      <dl className="identity-grid">
        {detailItems.map((item) => (
          <ResultField key={item.label} label={item.label} value={item.value} />
        ))}
      </dl>
      <button
        className="button"
        disabled={selectedServer === undefined || isRefreshing}
        onClick={onRefresh}
        type="button"
      >
        {isRefreshing ? "Refreshing..." : "Refresh tools"}
      </button>
    </section>
  );
}

function McpServersPanel({
  isLoading,
  isUpdating,
  onSelect,
  selectedServerId,
  servers,
}: {
  isLoading: boolean;
  isUpdating: boolean;
  onSelect: (serverId: string) => void;
  selectedServerId: string;
  servers: McpServer[];
}) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Servers</p>
          <h2>MCP server registry</h2>
        </div>
        <span className="status-pill">{isUpdating ? "Updating" : "Ready"}</span>
      </div>
      {isLoading ? <p className="muted">Loading MCP servers...</p> : null}
      {!isLoading && servers.length === 0 ? (
        <p className="muted">No MCP servers yet. Create one to start discovering tools.</p>
      ) : null}
      {servers.length > 0 ? (
        <ul className="timeline-list">
          {servers.map((server) => (
            <li className="timeline-list__item conversation-list-item" key={server.id}>
              <div>
                <span>{`${server.transport} · ${server.status}`}</span>
                <h3>{server.name}</h3>
                <p className="muted">{server.description ?? "No description"}</p>
                <p className="form-result">
                  <strong>Endpoint:</strong> {server.endpoint_url}
                </p>
                <p className="form-result">
                  <strong>Last discovered:</strong>{" "}
                  {server.last_discovered_at ?? "Not discovered"}
                </p>
              </div>
              <button
                className="button button--secondary"
                disabled={server.id === selectedServerId}
                onClick={() => onSelect(server.id)}
                type="button"
              >
                {server.id === selectedServerId ? "Selected" : "View tools"}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function McpToolsPanel({
  isLoading,
  selectedServer,
  tools,
}: {
  isLoading: boolean;
  selectedServer?: McpServer;
  tools: McpTool[];
}) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Discovered tools</p>
          <h2>{selectedServer?.name ?? "No server selected"}</h2>
        </div>
        <span className="status-pill">{isLoading ? "Loading" : `${tools.length} loaded`}</span>
      </div>
      {selectedServer === undefined ? (
        <p className="muted">Select an MCP server to view discovered tools.</p>
      ) : null}
      {selectedServer !== undefined && !isLoading && tools.length === 0 ? (
        <p className="muted">No tools discovered yet. Refresh tools to discover server capabilities.</p>
      ) : null}
      {tools.length > 0 ? (
        <ul className="timeline-list">
          {tools.map((tool) => (
            <li className="timeline-list__item" key={tool.id}>
              <span>{tool.status}</span>
              <p>{tool.name}</p>
              <p className="muted">{tool.description ?? "No description"}</p>
              <p className="form-result">
                <strong>Tool ID:</strong> <code>{tool.id}</code>
              </p>
              <p className="form-result">
                <strong>Last seen:</strong> {tool.last_seen_at}
              </p>
              <pre>{JSON.stringify(tool.input_schema, null, 2)}</pre>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function McpErrorBanner({ error, message }: { error?: Error; message?: string }) {
  const errorMessage =
    error instanceof HifyApiError
      ? `${error.message} (${error.code}, ${error.status})`
      : (message ?? error?.message ?? "MCP operation failed.");

  return (
    <section className="panel panel--danger" role="alert">
      <p className="panel__eyebrow">MCP error</p>
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

function handleFormError(
  error: unknown,
  setFormError: (message: string | null) => void,
  fallbackMessage: string,
) {
  if (!(error instanceof HifyApiError)) {
    setFormError(error instanceof Error ? error.message : fallbackMessage);
  }
}
