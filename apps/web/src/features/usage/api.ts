import { hifyApiClient, unwrapApiResponse } from "@/lib/api/client";

import type {
  SetUsageQuotaRequest,
  UsageCostByDay,
  UsageCostByModel,
  UsageCostSummary,
  UsagePeriodInput,
  UsageQuota,
  UsageQuotaStatus,
  UsageSummary,
} from "./types";

export async function getTeamUsageSummary(): Promise<UsageSummary> {
  return unwrapApiResponse(await hifyApiClient.GET("/usage/summary"));
}

export async function getUsageQuotaStatus(): Promise<UsageQuotaStatus> {
  return unwrapApiResponse(await hifyApiClient.GET("/usage/quota"));
}

export async function setUsageQuota(request: SetUsageQuotaRequest): Promise<UsageQuota> {
  return unwrapApiResponse(
    await hifyApiClient.PUT("/usage/quota", {
      body: request,
    }),
  );
}

export async function getUsageCostSummary(
  request: UsagePeriodInput = {},
): Promise<UsageCostSummary> {
  return unwrapApiResponse(
    await hifyApiClient.GET("/usage/cost-summary", {
      params: {
        query: toPeriodQuery(request),
      },
    }),
  );
}

export async function getUsageCostByModel(
  request: UsagePeriodInput = {},
): Promise<UsageCostByModel> {
  return unwrapApiResponse(
    await hifyApiClient.GET("/usage/cost-by-model", {
      params: {
        query: toPeriodQuery(request),
      },
    }),
  );
}

export async function getUsageCostByDay(request: UsagePeriodInput = {}): Promise<UsageCostByDay> {
  return unwrapApiResponse(
    await hifyApiClient.GET("/usage/cost-by-day", {
      params: {
        query: toPeriodQuery(request),
      },
    }),
  );
}

function toPeriodQuery(request: UsagePeriodInput): { from?: string | null; to?: string | null } {
  return {
    from: request.from ?? null,
    to: request.to ?? null,
  };
}
