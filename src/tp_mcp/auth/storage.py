"""Unified credential storage with automatic backend selection.

Uses system keyring when available, falls back to encrypted file storage.
The TP_AUTH_COOKIE environment variable is a supported first-class auth
source for headless servers, containers, and CI, and takes precedence
over both stored backends.
"""

import os

from tp_mcp.auth.credential import CredentialResult


def _keyring():
    """Lazily import the optional keyring backend."""
    from tp_mcp.auth import keyring

    return keyring


def _encrypted():
    """Lazily import the optional encrypted-file backend."""
    from tp_mcp.auth import encrypted

    return encrypted


def is_keyring_available() -> bool:
    """Whether the optional keyring backend is importable and usable."""
    try:
        return _keyring().is_keyring_available()
    except ImportError:
        return False

ENV_VAR_NAME = "TP_AUTH_COOKIE"


def get_storage_backend() -> str:
    """Get the current storage backend name.

    Returns:
        Name of the storage backend being used.
    """
    if os.environ.get(ENV_VAR_NAME):
        return "environment"
    if is_keyring_available():
        return "keyring"
    return "encrypted_file"


def store_credential(cookie: str) -> CredentialResult:
    """Store the TrainingPeaks auth cookie.

    Always stores in encrypted file for reliability. Also stores in keyring
    if available (but keyring access can be blocked by app-specific permissions
    on macOS when spawned from different applications like Claude Desktop).

    Args:
        cookie: The Production_tpAuth cookie value.

    Returns:
        CredentialResult with success status.
    """
    # Always store in encrypted file first (reliable fallback)
    encrypted_result = _encrypted().store_credential_encrypted(cookie)

    # Also try keyring if available (may fail due to app permissions on macOS,
    # or the Windows Credential Manager blob-size limit for large cookies).
    if is_keyring_available():
        try:
            keyring_result = _keyring().store_credential(cookie)
            if keyring_result.success:
                return CredentialResult(
                    success=True,
                    message="Credential stored in keyring and encrypted file",
                )
        except Exception:
            # Keyring write raised (e.g. WinError 1783 "The stub received bad
            # data" when the cookie exceeds the Windows Credential Manager
            # blob-size limit). The encrypted file write above already
            # succeeded, so fall back to it instead of crashing.
            pass

    return encrypted_result


def get_credential() -> CredentialResult:
    """Retrieve the TrainingPeaks auth cookie.

    Checks in order:
    1. TP_AUTH_COOKIE environment variable (supported auth method for
       headless servers, containers, and CI)
    2. System keyring
    3. Encrypted file

    Returns:
        CredentialResult with cookie if found.
    """
    # Check environment variable first (supported headless/container/CI
    # auth path; takes precedence over stored credentials)
    env_cookie = os.environ.get(ENV_VAR_NAME)
    if env_cookie:
        return CredentialResult(
            success=True,
            message="Credential from environment variable",
            cookie=env_cookie,
        )

    # Try keyring first
    if is_keyring_available():
        result = _keyring().get_credential()
        if result.success:
            return result

    # Fall back to encrypted file (may be absent on core-only installs)
    try:
        return _encrypted().get_credential_encrypted()
    except ImportError:
        return CredentialResult(
            success=False,
            message="No credential stored and no storage backends installed; set TP_AUTH_COOKIE.",
        )


def clear_credential() -> CredentialResult:
    """Clear stored credentials from all backends.

    Returns:
        CredentialResult with success status.
    """
    results = []

    # Clear from keyring
    if is_keyring_available():
        results.append(_keyring().clear_credential())

    # Clear from encrypted file
    try:
        results.append(_encrypted().clear_credential_encrypted())
    except ImportError:
        results.append(CredentialResult(success=False, message="Encrypted-file backend not installed"))

    # Return success if any succeeded
    if any(r.success for r in results):
        return CredentialResult(success=True, message="Credentials cleared")

    return CredentialResult(success=False, message="No credentials to clear")
