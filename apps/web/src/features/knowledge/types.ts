import type { components } from "@/lib/api/generated/schema";

export type CreateKnowledgeBaseRequest = components["schemas"]["CreateKnowledgeBaseRequest"];
export type IngestDocumentRequest = components["schemas"]["IngestDocumentRequest"];
export type KnowledgeBase = components["schemas"]["KnowledgeBaseResponse"];
export type KnowledgeDocument = components["schemas"]["KnowledgeDocumentResponse"];

export type GetKnowledgeBaseInput = {
  knowledgeBaseId: string;
};

export type ListKnowledgeDocumentsInput = {
  knowledgeBaseId: string;
};

export type IngestDocumentInput = IngestDocumentRequest & {
  knowledgeBaseId: string;
};
