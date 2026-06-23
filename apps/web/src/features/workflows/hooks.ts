"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createWorkflow,
  getWorkflow,
  listWorkflows,
  publishWorkflow,
  updateWorkflowDraft,
  validateWorkflowDraft,
} from "./api";
import type { GetWorkflowInput } from "./types";

export const workflowQueryKeys = {
  all: ["workflows"] as const,
  detail: (request: GetWorkflowInput) =>
    [...workflowQueryKeys.all, "detail", request.workflowId] as const,
  list: () => [...workflowQueryKeys.all, "list"] as const,
};

export const workflowMutationKeys = {
  createWorkflow: ["workflows", "create-workflow"] as const,
  publishWorkflow: ["workflows", "publish-workflow"] as const,
  updateWorkflowDraft: ["workflows", "update-workflow-draft"] as const,
  validateWorkflowDraft: ["workflows", "validate-workflow-draft"] as const,
};

export function useCreateWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createWorkflow,
    mutationKey: workflowMutationKeys.createWorkflow,
    onSuccess: async (workflow) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: workflowQueryKeys.list(),
        }),
        queryClient.invalidateQueries({
          queryKey: workflowQueryKeys.detail({ workflowId: workflow.id }),
        }),
      ]);
    },
  });
}

export function useWorkflows() {
  return useQuery({
    queryFn: listWorkflows,
    queryKey: workflowQueryKeys.list(),
  });
}

export function useWorkflow(request: GetWorkflowInput | null) {
  return useQuery({
    enabled: request !== null,
    queryFn: () => {
      if (request === null) {
        throw new Error("Workflow query requires a workflow ID.");
      }

      return getWorkflow(request);
    },
    queryKey:
      request === null
        ? [...workflowQueryKeys.all, "detail", "idle"]
        : workflowQueryKeys.detail(request),
  });
}

export function useUpdateWorkflowDraft() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateWorkflowDraft,
    mutationKey: workflowMutationKeys.updateWorkflowDraft,
    onSuccess: async (workflow) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: workflowQueryKeys.list(),
        }),
        queryClient.invalidateQueries({
          queryKey: workflowQueryKeys.detail({ workflowId: workflow.id }),
        }),
      ]);
    },
  });
}

export function useValidateWorkflowDraft() {
  return useMutation({
    mutationFn: validateWorkflowDraft,
    mutationKey: workflowMutationKeys.validateWorkflowDraft,
  });
}

export function usePublishWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: publishWorkflow,
    mutationKey: workflowMutationKeys.publishWorkflow,
    onSuccess: async (workflowVersion) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: workflowQueryKeys.list(),
        }),
        queryClient.invalidateQueries({
          queryKey: workflowQueryKeys.detail({ workflowId: workflowVersion.workflow_id }),
        }),
      ]);
    },
  });
}
