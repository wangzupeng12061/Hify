"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { cancelRun, createRun, getRun, listRunEvents } from "./api";
import type { ListRunEventsInput, RunIdInput } from "./types";

export const runQueryKeys = {
  all: ["runs"] as const,
  detail: (request: RunIdInput) => [...runQueryKeys.all, "detail", request.runId] as const,
  events: (request: ListRunEventsInput) =>
    [
      ...runQueryKeys.all,
      "events",
      request.runId,
      request.cursor ?? null,
      request.limit ?? 50,
    ] as const,
};

export const runMutationKeys = {
  cancelRun: ["runs", "cancel-run"] as const,
  createRun: ["runs", "create-run"] as const,
};

export function useCreateRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createRun,
    mutationKey: runMutationKeys.createRun,
    onSuccess: async (run) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: runQueryKeys.detail({ runId: run.id }) }),
        queryClient.invalidateQueries({
          queryKey: [...runQueryKeys.all, "events", run.id],
        }),
      ]);
    },
  });
}

export function useRun(request: RunIdInput | null) {
  return useQuery({
    enabled: request !== null,
    queryFn: () => {
      if (request === null) {
        throw new Error("Run query requires a run ID.");
      }

      return getRun(request);
    },
    queryKey:
      request === null
        ? [...runQueryKeys.all, "detail", "idle"]
        : runQueryKeys.detail(request),
  });
}

export function useRunEvents(request: ListRunEventsInput | null) {
  return useQuery({
    enabled: request !== null,
    queryFn: () => {
      if (request === null) {
        throw new Error("Run events query requires a run ID.");
      }

      return listRunEvents(request);
    },
    queryKey:
      request === null
        ? [...runQueryKeys.all, "events", "idle"]
        : runQueryKeys.events(request),
  });
}

export function useCancelRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: cancelRun,
    mutationKey: runMutationKeys.cancelRun,
    onSuccess: async (run) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: runQueryKeys.detail({ runId: run.id }) }),
        queryClient.invalidateQueries({
          queryKey: [...runQueryKeys.all, "events", run.id],
        }),
      ]);
    },
  });
}
