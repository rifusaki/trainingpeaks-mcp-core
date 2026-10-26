"""Authentication module for TrainingPeaks MCP Server.

The env-var credential path (TP_AUTH_COOKIE) is a first-class headless
auth method and must work without the optional keyring/cryptography
backends installed. Those are imported lazily so a core-only install
(tracking this fork as a package dependency) never needs them.
"""

from tp_mcp.auth.credential import CredentialResult
from tp_mcp.auth.validator import AuthResult, AuthStatus, validate_auth, validate_auth_sync

__all__ = [
    "AuthResult",
    "AuthStatus",
    "CredentialResult",
    "clear_credential",
    "get_credential",
    "get_storage_backend",
    "is_keyring_available",
    "store_credential",
    "validate_auth",
    "validate_auth_sync",
    "EncryptedCredentialStore",
]


def _storage():
    from tp_mcp.auth.storage import clear_credential, get_credential, get_storage_backend, store_credential

    return clear_credential, get_credential, get_storage_backend, store_credential


def __getattr__(name: str):
    if name in ("clear_credential", "get_credential", "get_storage_backend", "store_credential"):
        return _storage()[("clear_credential", "get_credential", "get_storage_backend", "store_credential").index(name)]
    if name == "is_keyring_available":
        from tp_mcp.auth.keyring import is_keyring_available

        return is_keyring_available
    if name == "EncryptedCredentialStore":
        from tp_mcp.auth.encrypted import EncryptedCredentialStore

        return EncryptedCredentialStore
    raise AttributeError(name)
