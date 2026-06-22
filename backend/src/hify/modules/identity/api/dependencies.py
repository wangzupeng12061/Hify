from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Header


DevelopmentUserIdHeader = Annotated[UUID | None, Header(alias="X-Hify-User-Id")]
DevelopmentTeamIdHeader = Annotated[UUID | None, Header(alias="X-Hify-Team-Id")]
