"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createTool, getTool, listTools } from "./api";
import type { GetToolInput } from "./types";

export const toolQueryKeys = {
  all: ["tools"] as const,
  detail: (request: GetToolInput) => [...toolQueryKeys.all, "detail", request.toolId] as const,
  list: () => [...toolQueryKeys.all, "list"] as const,
};

export const toolMutationKeys = {
  createTool: ["tools", "create-tool"] as const,
};

export function useCreateTool() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createTool,
    mutationKey: toolMutationKeys.createTool,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: toolQueryKeys.list(),
      });
    },
  });
}

export function useTools() {
  return useQuery({
    queryFn: listTools,
    queryKey: toolQueryKeys.list(),
  });
}

export function useTool(request: GetToolInput | null) {
  return useQuery({
    enabled: request !== null,
    queryFn: () => {
      if (request === null) {
        throw new Error("Tool query requires a tool ID.");
      }

      return getTool(request);
    },
    queryKey:
      request === null ? [...toolQueryKeys.all, "detail", "idle"] : toolQueryKeys.detail(request),
  });
}
