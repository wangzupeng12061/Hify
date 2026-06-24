"use client";

import { HifyApiError } from "@/lib/api/errors";

import { useCreateDevSession, useCurrentUser, useLogout } from "../hooks";

export function IdentityOverview() {
  const currentUserQuery = useCurrentUser();
  const createDevSessionMutation = useCreateDevSession();
  const logoutMutation = useLogout();

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
    return (
      <IdentityErrorState
        error={currentUserQuery.error}
        isDevLoginPending={createDevSessionMutation.isPending}
        onDevLogin={() =>
          createDevSessionMutation.mutate({
            display_name: "Hify Dev User",
            email: "dev@hify.local",
            team_name: "Hify Dev Team",
          })
        }
        onRetry={() => currentUserQuery.refetch()}
      />
    );
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
      <button
        className="button button--secondary"
        disabled={logoutMutation.isPending}
        onClick={() => logoutMutation.mutate()}
        type="button"
      >
        {logoutMutation.isPending ? "Signing out..." : "Sign out"}
      </button>
    </section>
  );
}

function IdentityErrorState({
  error,
  isDevLoginPending,
  onDevLogin,
  onRetry,
}: {
  error: Error;
  isDevLoginPending: boolean;
  onDevLogin: () => void;
  onRetry: () => void;
}) {
  const description =
    error instanceof HifyApiError
      ? `${error.message} (${error.code}, ${error.status})`
      : "The identity API returned an unexpected error.";

  return (
    <section className="panel panel--danger" role="alert">
      <p className="panel__eyebrow">Identity</p>
      <h2>Unable to load current actor</h2>
      <p className="muted">{description}</p>
      <p className="muted">
        For local verification, create a developer session. Production must use OIDC login.
      </p>
      <button className="button" disabled={isDevLoginPending} onClick={onDevLogin} type="button">
        {isDevLoginPending ? "Creating session..." : "Create dev session"}
      </button>
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
