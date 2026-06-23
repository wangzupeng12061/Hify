"use client";

import { useMutation } from "@tanstack/react-query";

import { createAgent, publishAgent } from "./api";

export const agentMutationKeys = {
  createAgent: ["agents", "create-agent"] as const,
  publishAgent: ["agents", "publish-agent"] as const,
};

export function useCreateAgent() {
  return useMutation({
    mutationFn: createAgent,
    mutationKey: agentMutationKeys.createAgent,
  });
}

export function usePublishAgent() {
  return useMutation({
    mutationFn: publishAgent,
    mutationKey: agentMutationKeys.publishAgent,
  });
}
