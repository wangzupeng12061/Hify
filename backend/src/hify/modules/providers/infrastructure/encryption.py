from __future__ import annotations

import hmac
from hashlib import sha256

from cryptography.fernet import Fernet

from hify.modules.providers.application.ports import CredentialEncryptor
from hify.modules.providers.domain.errors import ProviderValidationError
from hify.modules.providers.domain.value_objects import CredentialSecret


class FernetCredentialEncryptor(CredentialEncryptor):
    def __init__(self, encryption_key: str, *, key_version: int = 1) -> None:
        normalized_key = encryption_key.strip()
        if not normalized_key:
            raise ProviderValidationError("provider credential encryption key must not be blank")
        self._fingerprint_key = normalized_key.encode()
        self._fernet = Fernet(self._fingerprint_key)
        self._key_version = key_version

    def encrypt(self, plaintext: str) -> CredentialSecret:
        normalized = plaintext.strip()
        if not normalized:
            raise ProviderValidationError("provider credential must not be blank")
        ciphertext = self._fernet.encrypt(normalized.encode())
        fingerprint = hmac.new(
            self._fingerprint_key,
            normalized.encode(),
            sha256,
        ).hexdigest()[:16]
        return CredentialSecret(
            ciphertext=ciphertext,
            key_version=self._key_version,
            fingerprint=fingerprint,
        )

    def decrypt(self, secret: CredentialSecret) -> str:
        if secret.key_version != self._key_version:
            raise ProviderValidationError("provider credential key version is unsupported")
        return self._fernet.decrypt(secret.ciphertext).decode()


class MissingCredentialEncryptor(CredentialEncryptor):
    def encrypt(self, plaintext: str) -> CredentialSecret:
        raise ProviderValidationError("provider credential encryption is not configured")
