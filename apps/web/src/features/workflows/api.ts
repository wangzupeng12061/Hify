import { hifyApiClient, unwrapApiResponse } from "@/lib/api/client";

import type {
  CreateWorkflowRequest,
  GetWorkflowInput,
  PublishWorkflowInput,
  UpdateWorkflowDraftInput,
  ValidateWorkflowInput,
  Workflow,
  WorkflowValidation,
  WorkflowVersion,
} from "./types";

export async function createWorkflow(request: CreateWorkflowRequest): Promise<Workflow> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/workflows", {
      body: request,
    }),
  );
}

export async function listWorkflows(): Promise<Workflow[]> {
  return unwrapApiResponse(await hifyApiClient.GET("/workflows"));
}

export async function getWorkflow(request: GetWorkflowInput): Promise<Workflow> {
  return unwrapApiResponse(
    await hifyApiClient.GET("/workflows/{workflow_id}", {
      params: {
        path: {
          workflow_id: request.workflowId,
        },
      },
    }),
  );
}

export async function updateWorkflowDraft(request: UpdateWorkflowDraftInput): Promise<Workflow> {
  const { workflowId, ...body } = request;

  return unwrapApiResponse(
    await hifyApiClient.PUT("/workflows/{workflow_id}/draft", {
      body,
      params: {
        path: {
          workflow_id: workflowId,
        },
      },
    }),
  );
}

export async function validateWorkflowDraft(
  request: ValidateWorkflowInput,
): Promise<WorkflowValidation> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/workflows/{workflow_id}/validate", {
      params: {
        path: {
          workflow_id: request.workflowId,
        },
      },
    }),
  );
}

export async function publishWorkflow(request: PublishWorkflowInput): Promise<WorkflowVersion> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/workflows/{workflow_id}/publish", {
      params: {
        path: {
          workflow_id: request.workflowId,
        },
      },
    }),
  );
}
