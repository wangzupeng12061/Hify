import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  useCreateKnowledgeBase,
  useIngestDocument,
  useKnowledgeBases,
  useKnowledgeDocuments,
} from "@/features/knowledge";
import { hifyApiClient } from "@/lib/api/client";
import { createHifyQueryClient } from "@/lib/query/query-client";

const apiClientMock = vi.hoisted(() => ({
  GET: vi.fn(),
  POST: vi.fn(),
}));

vi.mock("@/lib/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/client")>();

  return {
    ...actual,
    hifyApiClient: apiClientMock,
  };
});

describe("knowledge hooks", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("lists knowledge bases", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: [createKnowledgeBaseResponse()],
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useKnowledgeBases(), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith("/knowledge-bases");
    expect(result.current.data?.[0]?.id).toBe("knowledge-base-1");
  });

  it("creates knowledge bases with the backend request contract", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: createKnowledgeBaseResponse(),
      response: new Response(null, { status: 201 }),
    });

    const { result } = renderHook(() => useCreateKnowledgeBase(), {
      wrapper: createQueryWrapper(),
    });

    const knowledgeBase = await result.current.mutateAsync({
      description: "Team docs",
      embedding_model_id: "model-1",
      name: "Runbooks",
    });

    expect(hifyApiClient.POST).toHaveBeenCalledWith("/knowledge-bases", {
      body: {
        description: "Team docs",
        embedding_model_id: "model-1",
        name: "Runbooks",
      },
    });
    expect(knowledgeBase.id).toBe("knowledge-base-1");
  });

  it("lists documents with path params", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: [createKnowledgeDocumentResponse()],
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(
      () => useKnowledgeDocuments({ knowledgeBaseId: "knowledge-base-1" }),
      { wrapper: createQueryWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith(
      "/knowledge-bases/{knowledge_base_id}/documents",
      {
        params: {
          path: {
            knowledge_base_id: "knowledge-base-1",
          },
        },
      },
    );
  });

  it("ingests documents with path params and request body", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: createKnowledgeDocumentResponse(),
      response: new Response(null, { status: 201 }),
    });

    const { result } = renderHook(() => useIngestDocument(), {
      wrapper: createQueryWrapper(),
    });

    await result.current.mutateAsync({
      content: "Restart the API with the deployment runbook.",
      knowledgeBaseId: "knowledge-base-1",
      source_uri: "s3://docs/runbook.md",
      title: "API runbook",
    });

    expect(hifyApiClient.POST).toHaveBeenCalledWith(
      "/knowledge-bases/{knowledge_base_id}/documents",
      {
        body: {
          content: "Restart the API with the deployment runbook.",
          source_uri: "s3://docs/runbook.md",
          title: "API runbook",
        },
        params: {
          path: {
            knowledge_base_id: "knowledge-base-1",
          },
        },
      },
    );
  });
});

function createQueryWrapper() {
  const queryClient = createHifyQueryClient();

  return function QueryWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

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
