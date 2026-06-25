"""add run activity and source event types

Revision ID: runs_20260625_0003
Revises: providers_20260624_0003
Create Date: 2026-06-25 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "runs_20260625_0003"
down_revision: str | None = "providers_20260624_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADED_EVENT_TYPE_CHECK = (
    "event_type IN ("
    "'run.created', 'run.started', 'run.succeeded', 'run.failed', "
    "'run.cancelled', 'run.interrupted', 'step.started', 'step.succeeded', "
    "'step.failed', 'output.text_delta', 'diagnostic', "
    "'activity.started', 'activity.completed', 'source.discovered'"
    ")"
)

DOWNGRADED_EVENT_TYPE_CHECK = (
    "event_type IN ("
    "'run.created', 'run.started', 'run.succeeded', 'run.failed', "
    "'run.cancelled', 'run.interrupted', 'step.started', 'step.succeeded', "
    "'step.failed', 'output.text_delta', 'diagnostic'"
    ")"
)


def upgrade() -> None:
    op.drop_constraint("ck_runs_events__event_type", "runs_events", type_="check")
    op.create_check_constraint(
        "ck_runs_events__event_type",
        "runs_events",
        UPGRADED_EVENT_TYPE_CHECK,
    )


def downgrade() -> None:
    op.drop_constraint("ck_runs_events__event_type", "runs_events", type_="check")
    op.create_check_constraint(
        "ck_runs_events__event_type",
        "runs_events",
        DOWNGRADED_EVENT_TYPE_CHECK,
    )
