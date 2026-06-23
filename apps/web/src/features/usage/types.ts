import type { components } from "@/lib/api/generated/schema";

export type SetUsageQuotaRequest = components["schemas"]["SetUsageQuotaRequest"];
export type UsageCostByDay = components["schemas"]["UsageCostByDayResponse"];
export type UsageCostByModel = components["schemas"]["UsageCostByModelResponse"];
export type UsageCostSummary = components["schemas"]["UsageCostSummaryResponse"];
export type UsageQuota = components["schemas"]["UsageQuotaResponse"];
export type UsageQuotaStatus = components["schemas"]["UsageQuotaStatusResponse"];
export type UsageSummary = components["schemas"]["UsageSummaryResponse"];

export type UsagePeriodInput = {
  from?: string | null;
  to?: string | null;
};
