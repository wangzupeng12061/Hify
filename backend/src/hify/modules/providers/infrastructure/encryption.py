from __future__ import annotations

from hashlib import sha256

from cryptography.fernet import Fernet

from hify.modules.providers.application.ports import CredentialEncryptor
from hify.modules.providers.domain.errors import ProviderValidationError
from hify.modules.providers.domain.value_objects import CredentialSecret


class FernetCredentialEncryptor(CredentialEncryptor):
    def __init__(self, encryption_key: str, *, key_version: int = 1) -> None:
        if not encryption_key.strip():
            raise ProviderValidationError("provider credential encryption key must not be blank")
        self._fernet = Fernet(encryption_key.encode())
        self._key_version = key_version

    def encrypt(self, plaintext: str) -> CredentialSecret:
        normalized = plaintext.strip()
        if not normalized:
            raise ProviderValidationError("provider credential must not be blank")
        ciphertext = self._fernet.encrypt(normalized.encode())
        fingerprint = sha256(normalized.encode()).hexdigest()[:16]
        return CredentialSecret(
            ciphertext=ciphertext,
            key_version=self._key_version,
            fingerprint=fingerprint,
        )


class MissingCredentialEncryptor(CredentialEncryptor):
    def encrypt(self, plaintext: str) -> CredentialSecret:
        raise ProviderValidationError("provider credential encryption is not configured")
