import type { components } from "@/lib/api/generated/schema";

export type CreateRunRequest = components["schemas"]["CreateRunRequest"];
export type Run = components["schemas"]["RunResponse"];
export type RunDiagnostics = components["schemas"]["RunDiagnosticsResponse"];
export type RunEvent = components["schemas"]["RunEventResponse"];
export type RunEventPage = components["schemas"]["RunEventPageResponse"];

export type RunIdInput = {
  runId: string;
};

export type ListRunEventsInput = RunIdInput & {
  cursor?: string | null;
  limit?: number;
};

export type ExecuteRunStreamInput = RunIdInput & {
  fetch?: typeof fetch;
  onEvent: (event: RunEvent) => void;
  signal?: AbortSignal;
};
