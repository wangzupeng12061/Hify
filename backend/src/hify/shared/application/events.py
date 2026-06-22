from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Protocol
from uuid import UUID


class IntegrationEvent(Protocol):
    event_id: UUID
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class OutboxMessage:
    event_id: UUID
    event_type: str
    payload: Mapping[str, object]
    occurred_at: datetime
