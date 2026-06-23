import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { KnowledgeManagement } from "@/features/knowledge/components/knowledge-management";

const hookMocks = vi.hoisted(() => ({
  createKnowledgeBase: vi.fn(),
  ingestDocument: vi.fn(),
}));

vi.mock("@/features/knowledge/hooks", () => ({
  useCreateKnowledgeBase: () => ({
    data: undefined,
    error: null,
    isPending: false,
    mutateAsync: hookMocks.createKnowledgeBase,
  }),
  useIngestDocument: () => ({
    data: undefined,
    error: null,
    isPending: false,
    mutateAsync: hookMocks.ingestDocument,
  }),
  useKnowledgeBases: () => ({
    data: [createKnowledgeBaseResponse()],
    error: null,
    isLoading: false,
  }),
  useKnowledgeDocuments: () => ({
    data: [createKnowledgeDocumentResponse()],
    error: null,
    isLoading: false,
  }),
}));

describe("KnowledgeManagement", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders knowledge bases and selected documents", () => {
    render(<KnowledgeManagement />);

    expect(screen.getAllByText("Runbooks").length).toBeGreaterThan(0);
    expect(screen.getByText("API runbook")).toBeTruthy();
    expect(screen.getByText("1 loaded")).toBeTruthy();
  });

  it("submits knowledge base creation values with cleaned optional fields", async () => {
    hookMocks.createKnowledgeBase.mockResolvedValueOnce(createKnowledgeBaseResponse());
    render(<KnowledgeManagement />);

    fireEvent.change(screen.getByLabelText("Knowledge base name"), {
      target: { value: " Team Docs " },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: " Internal docs " },
    });
    fireEvent.change(screen.getByLabelText("Embedding model ID"), {
      target: { value: " model-1 " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create knowledge base" }));

    await waitFor(() =>
      expect(hookMocks.createKnowledgeBase).toHaveBeenCalledWith({
        description: "Internal docs",
        embedding_model_id: "model-1",
        name: "Team Docs",
      }),
    );
  });

  it("submits document ingestion against the selected knowledge base", async () => {
    hookMocks.ingestDocument.mockResolvedValueOnce(createKnowledgeDocumentResponse());
    render(<KnowledgeManagement />);

    const ingestForm = screen.getByRole("button", { name: "Ingest document" }).closest("form");
    if (ingestForm === null) {
      throw new Error("Ingest document form was not rendered.");
    }

    fireEvent.change(within(ingestForm).getByLabelText("Document title"), {
      target: { value: " API Runbook " },
    });
    fireEvent.change(within(ingestForm).getByLabelText("Source URI"), {
      target: { value: " s3://docs/runbook.md " },
    });
    fireEvent.change(within(ingestForm).getByLabelText("Document content"), {
      target: { value: " Restart the API from the deployment runbook. " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ingest document" }));

    await waitFor(() =>
      expect(hookMocks.ingestDocument).toHaveBeenCalledWith({
        content: "Restart the API from the deployment runbook.",
        knowledgeBaseId: "knowledge-base-1",
        source_uri: "s3://docs/runbook.md",
        title: "API Runbook",
      }),
    );
  });
});

function createKnowledgeBaseResponse() {
  return {
    chunk_count: 3,
    created_at: "2026-06-23T00:00:00Z",
    description: "Team docs",
    document_count: 1,
    embedding_dimensions: 1536,
    embedding_model_id: "model-1",
    id: "knowledge-base-1",
    name: "Runbooks",
    status: "active",
    team_id: "team-1",
    updated_at: "2026-06-23T00:00:00Z",
  };
}

function createKnowledgeDocumentResponse() {
  return {
    chunk_count: 3,
    content_hash: "a".repeat(64),
    created_at: "2026-06-23T00:00:00Z",
    id: "document-1",
    knowledge_base_id: "knowledge-base-1",
    source_uri: "s3://docs/runbook.md",
    status: "completed",
    team_id: "team-1",
    title: "API runbook",
    updated_at: "2026-06-23T00:00:00Z",
  };
}
