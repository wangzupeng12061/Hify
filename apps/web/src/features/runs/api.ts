import {
  getConfiguredApiBaseUrl,
  hifyApiClient,
  normalizeApiBaseUrl,
  unwrapApiResponse,
} from "@/lib/api/client";
import { HifySseProtocolError, streamHifySse } from "@/lib/sse";

import type {
  CreateRunRequest,
  ExecuteRunStreamInput,
  ListRunEventsInput,
  Run,
  RunEvent,
  RunEventPage,
  RunIdInput,
} from "./types";

export async function createRun(request: CreateRunRequest): Promise<Run> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/runs", {
      body: request,
    }),
  );
}

export async function getRun(request: RunIdInput): Promise<Run> {
  return unwrapApiResponse(
    await hifyApiClient.GET("/runs/{run_id}", {
      params: {
        path: {
          run_id: request.runId,
        },
      },
    }),
  );
}

export async function cancelRun(request: RunIdInput): Promise<Run> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/runs/{run_id}/cancel", {
      params: {
        path: {
          run_id: request.runId,
        },
      },
    }),
  );
}

export async function listRunEvents(request: ListRunEventsInput): Promise<RunEventPage> {
  return unwrapApiResponse(
    await hifyApiClient.GET("/runs/{run_id}/events", {
      params: {
        path: {
          run_id: request.runId,
        },
        query: {
          cursor: request.cursor ?? null,
          limit: request.limit ?? 50,
        },
      },
    }),
  );
}

export async function executeRunStream(request: ExecuteRunStreamInput): Promise<void> {
  await streamHifySse({
    fetch: request.fetch,
    method: "POST",
    onMessage: (message) => {
      request.onEvent(parseRunStreamEvent(message.data));
    },
    signal: request.signal,
    url: createRunStreamUrl(request.runId),
  });
}

function createRunStreamUrl(runId: string): string {
  const baseUrl = normalizeApiBaseUrl(getConfiguredApiBaseUrl());
  return `${baseUrl}/runs/${encodeURIComponent(runId)}/execute-stream`;
}

function parseRunStreamEvent(data: string): RunEvent {
  let parsed: unknown;
  try {
    parsed = JSON.parse(data);
  } catch (error) {
    throw new HifySseProtocolError("Run stream event data is not valid JSON.", {
      cause: error,
    });
  }

  if (!isRunEvent(parsed)) {
    throw new HifySseProtocolError("Run stream event data does not match the run event contract.");
  }

  return parsed;
}

function isRunEvent(value: unknown): value is RunEvent {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.id === "string" &&
    typeof value.team_id === "string" &&
    typeof value.run_id === "string" &&
    typeof value.sequence_number === "number" &&
    typeof value.event_type === "string" &&
    isRecord(value.payload) &&
    typeof value.created_at === "string"
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
