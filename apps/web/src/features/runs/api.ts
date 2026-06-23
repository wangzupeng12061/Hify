import { hifyApiClient, unwrapApiResponse } from "@/lib/api/client";

import type { CreateRunRequest, ListRunEventsInput, Run, RunEventPage, RunIdInput } from "./types";

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
