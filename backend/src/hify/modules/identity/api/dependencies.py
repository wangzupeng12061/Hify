from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Header


UserIdHeader = Annotated[UUID, Header(alias="X-Hify-User-Id")]
TeamIdHeader = Annotated[UUID, Header(alias="X-Hify-Team-Id")]
