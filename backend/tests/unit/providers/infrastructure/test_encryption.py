from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from hify.modules.providers.domain.errors import ProviderValidationError
from hify.modules.providers.infrastructure.encryption import (
    FernetCredentialEncryptor,
    MissingCredentialEncryptor,
)


def test_fernet_encryptor_encrypts_secret_and_fingerprints_without_plaintext() -> None:
    key = Fernet.generate_key().decode()
    encryptor = FernetCredentialEncryptor(key, key_version=3)

    secret = encryptor.encrypt("sk-test")

    assert secret.key_version == 3
    assert secret.fingerprint
    assert b"sk-test" not in secret.ciphertext


def test_missing_encryptor_rejects_credential_writes() -> None:
    encryptor = MissingCredentialEncryptor()

    with pytest.raises(ProviderValidationError, match="not configured"):
        encryptor.encrypt("sk-test")
