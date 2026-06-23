"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createAgent, listAgents, publishAgent } from "./api";

export const agentQueryKeys = {
  all: ["agents"] as const,
  list: () => [...agentQueryKeys.all, "list"] as const,
};

export const agentMutationKeys = {
  createAgent: ["agents", "create-agent"] as const,
  publishAgent: ["agents", "publish-agent"] as const,
};

export function useAgents() {
  return useQuery({
    queryFn: listAgents,
    queryKey: agentQueryKeys.list(),
  });
}

export function useCreateAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createAgent,
    mutationKey: agentMutationKeys.createAgent,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: agentQueryKeys.list() });
    },
  });
}

export function usePublishAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: publishAgent,
    mutationKey: agentMutationKeys.publishAgent,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: agentQueryKeys.list() });
    },
  });
}
