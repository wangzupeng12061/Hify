"use client";

import { useMutation } from "@tanstack/react-query";

import { addProviderModel, createProvider, setProviderModelPricing } from "./api";

export const providerMutationKeys = {
  addModel: ["providers", "add-model"] as const,
  createProvider: ["providers", "create-provider"] as const,
  setPricing: ["providers", "set-pricing"] as const,
};

export function useCreateProvider() {
  return useMutation({
    mutationFn: createProvider,
    mutationKey: providerMutationKeys.createProvider,
  });
}

export function useAddProviderModel() {
  return useMutation({
    mutationFn: addProviderModel,
    mutationKey: providerMutationKeys.addModel,
  });
}

export function useSetProviderModelPricing() {
  return useMutation({
    mutationFn: setProviderModelPricing,
    mutationKey: providerMutationKeys.setPricing,
  });
}
