"""Credential result shared across auth backends.

Lives in its own dependency-free module so the storage backends
(keyring, encrypted file) can import it; those backends are optional
extras, but the env-var (TP_AUTH_COOKIE) credential path must import
without them.
"""

from dataclasses import dataclass, field


@dataclass
class CredentialResult:
    """Result of a credential operation."""

    success: bool
    message: str
    cookie: str | None = field(default=None, repr=False)

    def __repr__(self) -> str:
        """Safe repr that never exposes cookie value."""
        cookie_status = "present" if self.cookie else "None"
        return f"CredentialResult(success={self.success}, cookie=<{cookie_status}>, message={self.message!r})"
