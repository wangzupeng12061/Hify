"use client";

import { HifyApiError } from "@/lib/api/errors";

import { useCurrentUser } from "../hooks";

export function IdentityOverview() {
  const currentUserQuery = useCurrentUser();

  if (currentUserQuery.isPending) {
    return (
      <section className="panel" aria-busy="true">
        <p className="panel__eyebrow">Identity</p>
        <h2>Loading current user</h2>
        <p className="muted">Connecting to the Hify identity API.</p>
      </section>
    );
  }

  if (currentUserQuery.isError) {
    return <IdentityErrorState error={currentUserQuery.error} onRetry={() => currentUserQuery.refetch()} />;
  }

  const currentUser = currentUserQuery.data;

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Identity</p>
          <h2>Current actor</h2>
        </div>
        <span className="status-pill">Connected</span>
      </div>
      <dl className="identity-grid">
        <IdentityField label="User ID" value={currentUser.user_id} />
        <IdentityField label="Team ID" value={currentUser.team_id} />
        <IdentityField label="Membership ID" value={currentUser.membership_id} />
        <IdentityField label="Role" value={currentUser.role} />
        <IdentityField label="Permissions" value={currentUser.permissions.join(", ") || "None"} />
      </dl>
    </section>
  );
}

function IdentityErrorState({ error, onRetry }: { error: Error; onRetry: () => void }) {
  const description =
    error instanceof HifyApiError
      ? `${error.code} (${error.status})`
      : "The identity API returned an unexpected error.";

  return (
    <section className="panel panel--danger" role="alert">
      <p className="panel__eyebrow">Identity</p>
      <h2>Unable to load current actor</h2>
      <p className="muted">{description}</p>
      <button className="button" onClick={onRetry} type="button">
        Retry
      </button>
    </section>
  );
}

function IdentityField({ label, value }: { label: string; value: string }) {
  return (
    <div className="identity-field">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
