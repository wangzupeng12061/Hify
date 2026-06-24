from __future__ import annotations

from dataclasses import dataclass
import hashlib
import secrets


@dataclass(frozen=True, slots=True)
class SessionTokenPair:
    token: str
    token_hash: str


class SessionTokenService:
    def issue(self) -> SessionTokenPair:
        token = secrets.token_urlsafe(32)
        return SessionTokenPair(token=token, token_hash=self.hash_token(token))

    def hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
