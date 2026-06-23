"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createKnowledgeBase,
  getKnowledgeBase,
  ingestDocument,
  listKnowledgeBases,
  listKnowledgeDocuments,
} from "./api";
import type { GetKnowledgeBaseInput, ListKnowledgeDocumentsInput } from "./types";

export const knowledgeQueryKeys = {
  all: ["knowledge"] as const,
  detail: (request: GetKnowledgeBaseInput) =>
    [...knowledgeQueryKeys.all, "detail", request.knowledgeBaseId] as const,
  documents: (request: ListKnowledgeDocumentsInput) =>
    [...knowledgeQueryKeys.all, "documents", request.knowledgeBaseId] as const,
  list: () => [...knowledgeQueryKeys.all, "list"] as const,
};

export const knowledgeMutationKeys = {
  createKnowledgeBase: ["knowledge", "create-knowledge-base"] as const,
  ingestDocument: ["knowledge", "ingest-document"] as const,
};

export function useCreateKnowledgeBase() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createKnowledgeBase,
    mutationKey: knowledgeMutationKeys.createKnowledgeBase,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: knowledgeQueryKeys.list(),
      });
    },
  });
}

export function useKnowledgeBases() {
  return useQuery({
    queryFn: listKnowledgeBases,
    queryKey: knowledgeQueryKeys.list(),
  });
}

export function useKnowledgeBase(request: GetKnowledgeBaseInput | null) {
  return useQuery({
    enabled: request !== null,
    queryFn: () => {
      if (request === null) {
        throw new Error("Knowledge base query requires a knowledge base ID.");
      }

      return getKnowledgeBase(request);
    },
    queryKey:
      request === null
        ? [...knowledgeQueryKeys.all, "detail", "idle"]
        : knowledgeQueryKeys.detail(request),
  });
}

export function useKnowledgeDocuments(request: ListKnowledgeDocumentsInput | null) {
  return useQuery({
    enabled: request !== null,
    queryFn: () => {
      if (request === null) {
        throw new Error("Knowledge documents query requires a knowledge base ID.");
      }

      return listKnowledgeDocuments(request);
    },
    queryKey:
      request === null
        ? [...knowledgeQueryKeys.all, "documents", "idle"]
        : knowledgeQueryKeys.documents(request),
  });
}

export function useIngestDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ingestDocument,
    mutationKey: knowledgeMutationKeys.ingestDocument,
    onSuccess: async (_document, request) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: knowledgeQueryKeys.detail({ knowledgeBaseId: request.knowledgeBaseId }),
        }),
        queryClient.invalidateQueries({
          queryKey: knowledgeQueryKeys.documents({ knowledgeBaseId: request.knowledgeBaseId }),
        }),
        queryClient.invalidateQueries({
          queryKey: knowledgeQueryKeys.list(),
        }),
      ]);
    },
  });
}
