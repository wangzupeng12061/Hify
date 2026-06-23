from __future__ import annotations

from hify.modules.runs.contracts.dto import (
    RunDiagnosticStepInfo,
    RunDiagnosticsInfo,
    RunEventInfo,
    RunInfo,
    RunStepInfo,
)
from hify.modules.usage.contracts.dto import UsageSummaryInfo
from hify.modules.runs.domain.entities import AgentRun, RunEvent, RunStep


def run_info_from_domain(run: AgentRun) -> RunInfo:
    return RunInfo(
        id=run.id,
        team_id=run.team_id,
        conversation_id=run.conversation_id,
        agent_id=run.agent_id,
        agent_version_id=run.agent_version_id,
        status=run.status.value,
        step_count=run.step_count,
        event_count=run.event_count,
        created_at=run.created_at,
        updated_at=run.updated_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        duration_ms=run.duration_ms,
        error_code=run.error_code,
        error_message=run.error_message,
    )


def run_step_info_from_domain(step: RunStep) -> RunStepInfo:
    return RunStepInfo(
        id=step.id,
        team_id=step.team_id,
        run_id=step.run_id,
        sequence_number=step.sequence_number,
        step_type=step.step_type.value,
        status=step.status.value,
        name=step.name,
        started_at=step.started_at,
        completed_at=step.completed_at,
        duration_ms=step.duration_ms,
        error_code=step.error_code,
        error_message=step.error_message,
    )


def run_diagnostics_info_from_domain(
    run: AgentRun,
    steps: tuple[RunStep, ...],
    usage_summary: UsageSummaryInfo,
) -> RunDiagnosticsInfo:
    return RunDiagnosticsInfo(
        id=run.id,
        team_id=run.team_id,
        conversation_id=run.conversation_id,
        agent_id=run.agent_id,
        agent_version_id=run.agent_version_id,
        status=run.status.value,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        duration_ms=run.duration_ms,
        error_code=run.error_code,
        error_message=run.error_message,
        step_count=run.step_count,
        event_count=run.event_count,
        usage_input_tokens=usage_summary.input_tokens,
        usage_output_tokens=usage_summary.output_tokens,
        usage_total_tokens=usage_summary.total_tokens,
        usage_cost_amount=usage_summary.cost_amount,
        steps=tuple(
            RunDiagnosticStepInfo(
                id=step.id,
                sequence_number=step.sequence_number,
                step_type=step.step_type.value,
                status=step.status.value,
                name=step.name,
                started_at=step.started_at,
                completed_at=step.completed_at,
                duration_ms=step.duration_ms,
                error_code=step.error_code,
                error_message=step.error_message,
            )
            for step in steps
        ),
    )


def run_event_info_from_domain(event: RunEvent) -> RunEventInfo:
    return RunEventInfo(
        id=event.id,
        team_id=event.team_id,
        run_id=event.run_id,
        sequence_number=event.sequence_number,
        event_type=event.event_type.value,
        payload=event.payload,
        created_at=event.created_at,
    )
