"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { addProviderModel, createProvider, listProviderModels, setProviderModelPricing } from "./api";

export const providerQueryKeys = {
  all: ["providers"] as const,
  models: () => [...providerQueryKeys.all, "models"] as const,
};

export const providerMutationKeys = {
  addModel: ["providers", "add-model"] as const,
  createProvider: ["providers", "create-provider"] as const,
  setPricing: ["providers", "set-pricing"] as const,
};

export function useProviderModels() {
  return useQuery({
    queryFn: listProviderModels,
    queryKey: providerQueryKeys.models(),
  });
}

export function useCreateProvider() {
  return useMutation({
    mutationFn: createProvider,
    mutationKey: providerMutationKeys.createProvider,
  });
}

export function useAddProviderModel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: addProviderModel,
    mutationKey: providerMutationKeys.addModel,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: providerQueryKeys.models() });
    },
  });
}

export function useSetProviderModelPricing() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: setProviderModelPricing,
    mutationKey: providerMutationKeys.setPricing,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: providerQueryKeys.models() });
    },
  });
}
