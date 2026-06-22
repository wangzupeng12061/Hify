from __future__ import annotations

from dataclasses import dataclass

from hify.modules.identity.application.dto import user_profile_from_domain
from hify.modules.identity.application.ports import IdentityUnitOfWorkFactory
from hify.modules.identity.contracts.dto import UserProfile
from hify.modules.identity.domain.entities import User
from hify.modules.identity.domain.errors import UserEmailAlreadyExistsError
from hify.modules.identity.domain.value_objects import EmailAddress
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class CreateUserCommand:
    email: str
    display_name: str


class CreateUserHandler:
    def __init__(self, unit_of_work_factory: IdentityUnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: CreateUserCommand) -> UserProfile:
        email = EmailAddress.parse(command.email)
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            existing_user = await unit_of_work.users.get_by_email(email)
            if existing_user is not None:
                raise UserEmailAlreadyExistsError("user email already exists")

            user = User.create(email=email, display_name=command.display_name, now=now)
            await unit_of_work.users.add(user)
            await unit_of_work.commit()

        return user_profile_from_domain(user)
