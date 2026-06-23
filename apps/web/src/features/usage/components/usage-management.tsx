"use client";

import { useState, type FormEvent } from "react";

import { HifyApiError } from "@/lib/api/errors";

import {
  useSetUsageQuota,
  useTeamUsageSummary,
  useUsageCostByDay,
  useUsageCostByModel,
  useUsageCostSummary,
  useUsageQuotaStatus,
} from "../hooks";
import type {
  UsageCostByDay,
  UsageCostByModel,
  UsageCostSummary,
  UsageQuotaStatus,
  UsageSummary,
} from "../types";

type QuotaFormState = {
  monthlyTokenLimit: string;
};

type PeriodFormState = {
  from: string;
  to: string;
};

const initialQuotaForm: QuotaFormState = {
  monthlyTokenLimit: "",
};

const initialPeriodForm: PeriodFormState = {
  from: "",
  to: "",
};

export function UsageManagement() {
  const [quotaForm, setQuotaForm] = useState(initialQuotaForm);
  const [periodForm, setPeriodForm] = useState(initialPeriodForm);
  const [activePeriod, setActivePeriod] = useState(initialPeriodForm);
  const [formError, setFormError] = useState<string | null>(null);
  const periodQuery = toPeriodQuery(activePeriod);

  const teamSummaryQuery = useTeamUsageSummary();
  const quotaStatusQuery = useUsageQuotaStatus();
  const costSummaryQuery = useUsageCostSummary(periodQuery);
  const costByModelQuery = useUsageCostByModel(periodQuery);
  const costByDayQuery = useUsageCostByDay(periodQuery);
  const setQuotaMutation = useSetUsageQuota();

  async function handleSetQuota(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    try {
      await setQuotaMutation.mutateAsync({
        monthly_token_limit: parseMonthlyTokenLimit(quotaForm.monthlyTokenLimit),
      });
      setQuotaForm(initialQuotaForm);
    } catch (error) {
      handleFormError(error, setFormError, "Unable to update usage quota.");
    }
  }

  function handleApplyPeriod(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setActivePeriod({
      from: toDateTimeOrEmpty(periodForm.from),
      to: toDateTimeOrEmpty(periodForm.to),
    });
  }

  const operationError =
    teamSummaryQuery.error ??
    quotaStatusQuery.error ??
    costSummaryQuery.error ??
    costByModelQuery.error ??
    costByDayQuery.error ??
    setQuotaMutation.error;

  return (
    <div className="page-stack">
      <section className="hero">
        <p className="hero__eyebrow">Usage</p>
        <h2>Track token usage, costs, quotas, and budget risk.</h2>
        <p>
          This first version surfaces the backend usage contract: team token totals, cost summaries,
          quota status, budget risk, model cost breakdowns, and daily cost trends.
        </p>
      </section>

      {formError ? <UsageErrorBanner message={formError} /> : null}
      {operationError ? <UsageErrorBanner error={operationError} /> : null}

      <section className="provider-layout">
        <QuotaForm
          form={quotaForm}
          isSubmitting={setQuotaMutation.isPending}
          onChange={setQuotaForm}
          onSubmit={handleSetQuota}
          quotaStatus={quotaStatusQuery.data}
        />
        <PeriodForm
          activePeriod={activePeriod}
          form={periodForm}
          onChange={setPeriodForm}
          onSubmit={handleApplyPeriod}
        />
      </section>

      <UsageOverview
        costSummary={costSummaryQuery.data}
        isLoading={
          teamSummaryQuery.isLoading || quotaStatusQuery.isLoading || costSummaryQuery.isLoading
        }
        quotaStatus={quotaStatusQuery.data}
        teamSummary={teamSummaryQuery.data}
      />

      <CostByModelPanel
        costByModel={costByModelQuery.data}
        isLoading={costByModelQuery.isLoading}
      />

      <CostByDayPanel costByDay={costByDayQuery.data} isLoading={costByDayQuery.isLoading} />
    </div>
  );
}

function QuotaForm({
  form,
  isSubmitting,
  onChange,
  onSubmit,
  quotaStatus,
}: {
  form: QuotaFormState;
  isSubmitting: boolean;
  onChange: (form: QuotaFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  quotaStatus?: UsageQuotaStatus;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Quota</p>
      <h2>Set monthly token limit</h2>
      <p className="muted">
        Leave the field empty to remove the monthly token quota for the team.
      </p>
      <label className="form-field">
        Monthly token limit
        <input
          min={0}
          name="monthlyTokenLimit"
          onChange={(event) => onChange({ monthlyTokenLimit: event.target.value })}
          placeholder={quotaStatus?.monthly_token_limit?.toString() ?? "Unlimited"}
          type="number"
          value={form.monthlyTokenLimit}
        />
      </label>
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Saving..." : "Save quota"}
      </button>
    </form>
  );
}

function PeriodForm({
  activePeriod,
  form,
  onChange,
  onSubmit,
}: {
  activePeriod: PeriodFormState;
  form: PeriodFormState;
  onChange: (form: PeriodFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Period</p>
      <h2>Filter cost views</h2>
      <label className="form-field">
        From date
        <input
          name="from"
          onChange={(event) => onChange({ ...form, from: event.target.value })}
          type="date"
          value={form.from}
        />
      </label>
      <label className="form-field">
        To date
        <input
          name="to"
          onChange={(event) => onChange({ ...form, to: event.target.value })}
          type="date"
          value={form.to}
        />
      </label>
      <button className="button" type="submit">
        Apply period
      </button>
      <p className="form-result">
        <strong>Active period:</strong> {formatPeriod(activePeriod)}
      </p>
    </form>
  );
}

function UsageOverview({
  costSummary,
  isLoading,
  quotaStatus,
  teamSummary,
}: {
  costSummary?: UsageCostSummary;
  isLoading: boolean;
  quotaStatus?: UsageQuotaStatus;
  teamSummary?: UsageSummary;
}) {
  const items = [
    { label: "Team total tokens", value: formatNumber(teamSummary?.total_tokens) },
    { label: "Input tokens", value: formatNumber(teamSummary?.input_tokens) },
    { label: "Output tokens", value: formatNumber(teamSummary?.output_tokens) },
    { label: "Team cost", value: formatCurrency(teamSummary?.cost_amount) },
    { label: "Period cost", value: formatCurrency(costSummary?.cost_amount) },
    { label: "Period tokens", value: formatNumber(costSummary?.total_tokens) },
    { label: "Monthly limit", value: formatOptionalNumber(quotaStatus?.monthly_token_limit) },
    { label: "Remaining tokens", value: formatOptionalNumber(quotaStatus?.remaining_tokens) },
    { label: "Used this period", value: formatNumber(quotaStatus?.used_tokens) },
    {
      label: "Budget status",
      value: costSummary?.is_quota_exceeded || quotaStatus?.is_exceeded ? "Exceeded" : "Within limit",
    },
  ];

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Overview</p>
          <h2>Team usage and budget status</h2>
        </div>
        <span className="status-pill">{isLoading ? "Loading" : "Current"}</span>
      </div>
      <dl className="identity-grid">
        {items.map((item) => (
          <ResultField key={item.label} label={item.label} value={item.value} />
        ))}
      </dl>
    </section>
  );
}

function CostByModelPanel({
  costByModel,
  isLoading,
}: {
  costByModel?: UsageCostByModel;
  isLoading: boolean;
}) {
  const items = costByModel?.items ?? [];

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Models</p>
          <h2>Cost by model</h2>
        </div>
        <span className="status-pill">{isLoading ? "Loading" : `${items.length} loaded`}</span>
      </div>
      {items.length === 0 && !isLoading ? (
        <p className="muted">No model usage has been recorded for this period.</p>
      ) : null}
      {items.length > 0 ? (
        <ul className="timeline-list">
          {items.map((item) => (
            <li className="timeline-list__item" key={item.provider_model_id}>
              <span>{item.provider}</span>
              <p>{item.model}</p>
              <p className="form-result">
                <strong>Cost:</strong> {formatCurrency(item.cost_amount)} ·{" "}
                <strong>Tokens:</strong> {formatNumber(item.total_tokens)}
              </p>
              <p className="form-result">
                <strong>Input:</strong> {formatNumber(item.input_tokens)} ·{" "}
                <strong>Output:</strong> {formatNumber(item.output_tokens)}
              </p>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function CostByDayPanel({
  costByDay,
  isLoading,
}: {
  costByDay?: UsageCostByDay;
  isLoading: boolean;
}) {
  const items = costByDay?.items ?? [];

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Daily</p>
          <h2>Cost by day</h2>
        </div>
        <span className="status-pill">{isLoading ? "Loading" : `${items.length} loaded`}</span>
      </div>
      {items.length === 0 && !isLoading ? (
        <p className="muted">No daily usage has been recorded for this period.</p>
      ) : null}
      {items.length > 0 ? (
        <ul className="timeline-list">
          {items.map((item) => (
            <li className="timeline-list__item" key={item.usage_date}>
              <span>{item.usage_date}</span>
              <p>{formatCurrency(item.cost_amount)}</p>
              <p className="form-result">
                <strong>Total tokens:</strong> {formatNumber(item.total_tokens)}
              </p>
              <p className="form-result">
                <strong>Input:</strong> {formatNumber(item.input_tokens)} ·{" "}
                <strong>Output:</strong> {formatNumber(item.output_tokens)}
              </p>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function UsageErrorBanner({ error, message }: { error?: Error; message?: string }) {
  const errorMessage =
    error instanceof HifyApiError
      ? `${error.message} (${error.code}, ${error.status})`
      : (message ?? error?.message ?? "Usage operation failed.");

  return (
    <section className="panel panel--danger" role="alert">
      <p className="panel__eyebrow">Usage error</p>
      <h2>Operation failed</h2>
      <p className="muted">{errorMessage}</p>
    </section>
  );
}

function ResultField({ label, value }: { label: string; value: string }) {
  return (
    <div className="identity-field">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function parseMonthlyTokenLimit(value: string): number | null {
  const trimmedValue = value.trim();
  if (trimmedValue === "") {
    return null;
  }

  const parsedValue = Number(trimmedValue);
  if (!Number.isInteger(parsedValue) || parsedValue < 0) {
    throw new Error("Monthly token limit must be a non-negative integer.");
  }

  return parsedValue;
}

function toDateTimeOrEmpty(value: string): string {
  return value === "" ? "" : `${value}T00:00:00.000Z`;
}

function toPeriodQuery(period: PeriodFormState): { from?: string | null; to?: string | null } {
  return {
    from: period.from || null,
    to: period.to || null,
  };
}

function formatPeriod(period: PeriodFormState): string {
  const from = period.from ? period.from.slice(0, 10) : "default start";
  const to = period.to ? period.to.slice(0, 10) : "default end";
  return `${from} to ${to}`;
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Not available";
  }

  return new Intl.NumberFormat("en-US").format(value);
}

function formatOptionalNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Unlimited";
  }

  return formatNumber(value);
}

function formatCurrency(value: string | number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Not available";
  }

  return `$${Number(value).toFixed(6)}`;
}

function handleFormError(
  error: unknown,
  setFormError: (message: string | null) => void,
  fallbackMessage: string,
) {
  if (!(error instanceof HifyApiError)) {
    setFormError(error instanceof Error ? error.message : fallbackMessage);
  }
}
