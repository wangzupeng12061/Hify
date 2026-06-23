import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WorkflowsManagement } from "@/features/workflows/components/workflows-management";

const hookMocks = vi.hoisted(() => ({
  createWorkflow: vi.fn(),
  publishWorkflow: vi.fn(),
  updateWorkflowDraft: vi.fn(),
  validateWorkflowDraft: vi.fn(),
}));

vi.mock("@/features/workflows/hooks", () => ({
  useCreateWorkflow: () => ({
    data: undefined,
    error: null,
    isPending: false,
    mutateAsync: hookMocks.createWorkflow,
  }),
  usePublishWorkflow: () => ({
    data: createWorkflowVersionResponse(),
    error: null,
    isPending: false,
    mutateAsync: hookMocks.publishWorkflow,
  }),
  useUpdateWorkflowDraft: () => ({
    data: undefined,
    error: null,
    isPending: false,
    mutateAsync: hookMocks.updateWorkflowDraft,
  }),
  useValidateWorkflowDraft: () => ({
    data: { is_valid: true, issues: [] },
    error: null,
    isPending: false,
    mutateAsync: hookMocks.validateWorkflowDraft,
  }),
  useWorkflow: () => ({
    data: createWorkflowResponse(),
    error: null,
    isLoading: false,
  }),
  useWorkflows: () => ({
    data: [createWorkflowResponse()],
    error: null,
    isLoading: false,
  }),
}));

describe("WorkflowsManagement", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders workflow list and selected draft details", () => {
    render(<WorkflowsManagement />);

    expect(screen.getAllByText("Support Flow").length).toBeGreaterThan(0);
    expect(screen.getByText("1 loaded")).toBeTruthy();
    expect(screen.getByText("2 nodes / 1 edges")).toBeTruthy();
    expect(screen.getByText("Workflow draft is valid")).toBeTruthy();
    expect(screen.getByText("Published v1")).toBeTruthy();
  });

  it("submits workflow creation values with parsed draft JSON", async () => {
    hookMocks.createWorkflow.mockResolvedValueOnce(createWorkflowResponse());
    render(<WorkflowsManagement />);

    fireEvent.change(screen.getByLabelText("Workflow name"), {
      target: { value: " Escalation Flow " },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: " Customer escalation " },
    });
    fireEvent.change(screen.getByLabelText("Initial draft JSON"), {
      target: { value: JSON.stringify(createWorkflowDefinition()) },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create workflow" }));

    await waitFor(() =>
      expect(hookMocks.createWorkflow).toHaveBeenCalledWith({
        description: "Customer escalation",
        draft_definition: createWorkflowDefinition(),
        name: "Escalation Flow",
      }),
    );
  });

  it("updates the selected workflow draft from the editor", async () => {
    hookMocks.updateWorkflowDraft.mockResolvedValueOnce(createWorkflowResponse());
    render(<WorkflowsManagement />);

    const draftForm = screen.getByRole("button", { name: "Save draft" }).closest("form");
    if (draftForm === null) {
      throw new Error("Draft editor form was not rendered.");
    }

    fireEvent.change(within(draftForm).getByLabelText("Draft JSON"), {
      target: { value: JSON.stringify(createWorkflowDefinition()) },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));

    await waitFor(() =>
      expect(hookMocks.updateWorkflowDraft).toHaveBeenCalledWith({
        draft_definition: createWorkflowDefinition(),
        workflowId: "workflow-1",
      }),
    );
  });

  it("validates and publishes the selected workflow", async () => {
    hookMocks.validateWorkflowDraft.mockResolvedValueOnce({ is_valid: true, issues: [] });
    hookMocks.publishWorkflow.mockResolvedValueOnce(createWorkflowVersionResponse());
    render(<WorkflowsManagement />);

    fireEvent.click(screen.getByRole("button", { name: "Validate" }));
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));

    await waitFor(() =>
      expect(hookMocks.validateWorkflowDraft).toHaveBeenCalledWith({
        workflowId: "workflow-1",
      }),
    );
    await waitFor(() =>
      expect(hookMocks.publishWorkflow).toHaveBeenCalledWith({
        workflowId: "workflow-1",
      }),
    );
  });
});

function createWorkflowDefinition() {
  return {
    edges: [{ source_node_id: "start", target_node_id: "end" }],
    nodes: [
      { config: {}, id: "start", kind: "start" },
      { config: {}, id: "end", kind: "end" },
    ],
  };
}

function createWorkflowResponse() {
  return {
    created_at: "2026-06-23T00:00:00Z",
    description: "Support workflow",
    draft_definition: createWorkflowDefinition(),
    id: "workflow-1",
    latest_version_number: 0,
    name: "Support Flow",
    status: "draft",
    team_id: "team-1",
    updated_at: "2026-06-23T00:00:00Z",
  };
}

function createWorkflowVersionResponse() {
  return {
    created_at: "2026-06-23T00:00:00Z",
    definition: createWorkflowDefinition(),
    description: "Support workflow",
    id: "workflow-version-1",
    name: "Support Flow",
    team_id: "team-1",
    version_number: 1,
    workflow_id: "workflow-1",
  };
}
