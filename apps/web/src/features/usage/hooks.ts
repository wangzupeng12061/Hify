"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getTeamUsageSummary,
  getUsageCostByDay,
  getUsageCostByModel,
  getUsageCostSummary,
  getUsageQuotaStatus,
  setUsageQuota,
} from "./api";
import type { UsagePeriodInput } from "./types";

export const usageQueryKeys = {
  all: ["usage"] as const,
  costByDay: (request: UsagePeriodInput) =>
    [...usageQueryKeys.all, "cost-by-day", request.from ?? null, request.to ?? null] as const,
  costByModel: (request: UsagePeriodInput) =>
    [...usageQueryKeys.all, "cost-by-model", request.from ?? null, request.to ?? null] as const,
  costSummary: (request: UsagePeriodInput) =>
    [...usageQueryKeys.all, "cost-summary", request.from ?? null, request.to ?? null] as const,
  quota: () => [...usageQueryKeys.all, "quota"] as const,
  summary: () => [...usageQueryKeys.all, "summary"] as const,
};

export const usageMutationKeys = {
  setQuota: ["usage", "set-quota"] as const,
};

export function useTeamUsageSummary() {
  return useQuery({
    queryFn: getTeamUsageSummary,
    queryKey: usageQueryKeys.summary(),
  });
}

export function useUsageQuotaStatus() {
  return useQuery({
    queryFn: getUsageQuotaStatus,
    queryKey: usageQueryKeys.quota(),
  });
}

export function useUsageCostSummary(request: UsagePeriodInput = {}) {
  return useQuery({
    queryFn: () => getUsageCostSummary(request),
    queryKey: usageQueryKeys.costSummary(request),
  });
}

export function useUsageCostByModel(request: UsagePeriodInput = {}) {
  return useQuery({
    queryFn: () => getUsageCostByModel(request),
    queryKey: usageQueryKeys.costByModel(request),
  });
}

export function useUsageCostByDay(request: UsagePeriodInput = {}) {
  return useQuery({
    queryFn: () => getUsageCostByDay(request),
    queryKey: usageQueryKeys.costByDay(request),
  });
}

export function useSetUsageQuota() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: setUsageQuota,
    mutationKey: usageMutationKeys.setQuota,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: usageQueryKeys.quota(),
        }),
        queryClient.invalidateQueries({
          queryKey: usageQueryKeys.summary(),
        }),
        queryClient.invalidateQueries({
          queryKey: [...usageQueryKeys.all, "cost-summary"],
        }),
      ]);
    },
  });
}
