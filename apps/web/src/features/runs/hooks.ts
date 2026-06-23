"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  cancelRun,
  createRun,
  executeRunStream,
  getRun,
  getRunDiagnostics,
  listRunEvents,
} from "./api";
import type { ListRunEventsInput, RunEvent, RunIdInput } from "./types";

export type RunStreamStatus =
  | "idle"
  | "connecting"
  | "streaming"
  | "completed"
  | "aborted"
  | "error";

export type StartRunStreamInput = RunIdInput & {
  onComplete?: () => void;
  onError?: (error: Error) => void;
  onEvent: (event: RunEvent) => void;
};

export const runQueryKeys = {
  all: ["runs"] as const,
  detail: (request: RunIdInput) => [...runQueryKeys.all, "detail", request.runId] as const,
  diagnostics: (request: RunIdInput) =>
    [...runQueryKeys.all, "diagnostics", request.runId] as const,
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

export function useRunDiagnostics(request: RunIdInput | null) {
  return useQuery({
    enabled: request !== null,
    queryFn: () => {
      if (request === null) {
        throw new Error("Run diagnostics query requires a run ID.");
      }

      return getRunDiagnostics(request);
    },
    queryKey:
      request === null
        ? [...runQueryKeys.all, "diagnostics", "idle"]
        : runQueryKeys.diagnostics(request),
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
        queryClient.invalidateQueries({
          queryKey: runQueryKeys.diagnostics({ runId: run.id }),
        }),
      ]);
    },
  });
}

export function useRunStream() {
  const abortControllerRef = useRef<AbortController | null>(null);
  const streamRequestIdRef = useRef(0);
  const [status, setStatus] = useState<RunStreamStatus>("idle");
  const [error, setError] = useState<Error | null>(null);

  const stop = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
  }, []);

  const start = useCallback(
    async (request: StartRunStreamInput) => {
      stop();

      const abortController = new AbortController();
      const streamRequestId = streamRequestIdRef.current + 1;
      streamRequestIdRef.current = streamRequestId;
      abortControllerRef.current = abortController;
      setError(null);
      setStatus("connecting");

      try {
        await executeRunStream({
          onEvent: (event) => {
            if (streamRequestIdRef.current !== streamRequestId) {
              return;
            }

            setStatus("streaming");
            request.onEvent(event);
          },
          runId: request.runId,
          signal: abortController.signal,
        });

        if (streamRequestIdRef.current !== streamRequestId) {
          return;
        }

        abortControllerRef.current = null;
        setStatus(abortController.signal.aborted ? "aborted" : "completed");
        request.onComplete?.();
      } catch (caughtError) {
        if (streamRequestIdRef.current !== streamRequestId) {
          return;
        }

        abortControllerRef.current = null;
        if (isAbortError(caughtError)) {
          setStatus("aborted");
          return;
        }

        const error = caughtError instanceof Error ? caughtError : new Error("Run stream failed.");
        setError(error);
        setStatus("error");
        request.onError?.(error);
      }
    },
    [stop],
  );

  useEffect(() => stop, [stop]);

  return {
    error,
    isStreaming: status === "connecting" || status === "streaming",
    start,
    status,
    stop,
  };
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
