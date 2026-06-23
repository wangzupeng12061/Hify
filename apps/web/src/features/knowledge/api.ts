import { hifyApiClient, unwrapApiResponse } from "@/lib/api/client";

import type {
  CreateKnowledgeBaseRequest,
  GetKnowledgeBaseInput,
  IngestDocumentInput,
  KnowledgeBase,
  KnowledgeDocument,
  ListKnowledgeDocumentsInput,
} from "./types";

export async function createKnowledgeBase(
  request: CreateKnowledgeBaseRequest,
): Promise<KnowledgeBase> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/knowledge-bases", {
      body: request,
    }),
  );
}

export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  return unwrapApiResponse(await hifyApiClient.GET("/knowledge-bases"));
}

export async function getKnowledgeBase(request: GetKnowledgeBaseInput): Promise<KnowledgeBase> {
  return unwrapApiResponse(
    await hifyApiClient.GET("/knowledge-bases/{knowledge_base_id}", {
      params: {
        path: {
          knowledge_base_id: request.knowledgeBaseId,
        },
      },
    }),
  );
}

export async function listKnowledgeDocuments(
  request: ListKnowledgeDocumentsInput,
): Promise<KnowledgeDocument[]> {
  return unwrapApiResponse(
    await hifyApiClient.GET("/knowledge-bases/{knowledge_base_id}/documents", {
      params: {
        path: {
          knowledge_base_id: request.knowledgeBaseId,
        },
      },
    }),
  );
}

export async function ingestDocument(request: IngestDocumentInput): Promise<KnowledgeDocument> {
  const { knowledgeBaseId, ...body } = request;

  return unwrapApiResponse(
    await hifyApiClient.POST("/knowledge-bases/{knowledge_base_id}/documents", {
      body,
      params: {
        path: {
          knowledge_base_id: knowledgeBaseId,
        },
      },
    }),
  );
}
