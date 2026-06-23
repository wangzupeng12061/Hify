import type { components } from "@/lib/api/generated/schema";

export type CreateWorkflowRequest = components["schemas"]["CreateWorkflowRequest"];
export type UpdateWorkflowDraftRequest = components["schemas"]["UpdateWorkflowDraftRequest"];
export type Workflow = components["schemas"]["WorkflowResponse"];
export type WorkflowValidation = components["schemas"]["WorkflowValidationResponse"];
export type WorkflowVersion = components["schemas"]["WorkflowVersionResponse"];

export type GetWorkflowInput = {
  workflowId: string;
};

export type UpdateWorkflowDraftInput = UpdateWorkflowDraftRequest & {
  workflowId: string;
};

export type PublishWorkflowInput = {
  workflowId: string;
};

export type ValidateWorkflowInput = {
  workflowId: string;
};
