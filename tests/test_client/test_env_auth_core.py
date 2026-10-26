"""Regression tests for the core-only install surface.

Catence (and any headless consumer) installs this fork as a client/auth
package without the keyring, cryptography, or MCP server extras and
authenticates exclusively via the TP_AUTH_COOKIE environment variable.
The full no-backends install is additionally exercised by the CI
"core-only" job in a real venv; these unit tests pin the env-auth
behavior and credential hygiene without requiring the backends.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tp_mcp.auth.credential import CredentialResult

TEST_COOKIE = "test_cookie_value_12345"


@pytest.fixture
def env_cookie(monkeypatch):
    monkeypatch.setenv("TP_AUTH_COOKIE", TEST_COOKIE)
    yield TEST_COOKIE


@pytest.fixture
def no_stored_backend(monkeypatch):
    """Simulate an environment with no usable keyring and no stored file credential."""
    import tp_mcp.auth.storage as storage

    monkeypatch.setattr(storage, "is_keyring_available", lambda: False)
    monkeypatch.setattr(
        storage,
        "_encrypted",
        lambda: pytest.fail("encrypted-file backend must not be consulted when TP_AUTH_COOKIE is set"),
        raising=False,
    )
    yield storage


def test_env_credential_wins_without_stored_backends(env_cookie, no_stored_backend):
    cred = no_stored_backend.get_credential()
    assert cred.success is True
    assert cred.cookie == TEST_COOKIE
    assert no_stored_backend.get_storage_backend() == "environment"


def test_no_env_falls_back_and_reports_missing(monkeypatch):
    monkeypatch.delenv("TP_AUTH_COOKIE", raising=False)
    import tp_mcp.auth.storage as storage

    monkeypatch.setattr(storage, "is_keyring_available", lambda: False)
    monkeypatch.setattr(storage, "_encrypted", lambda: (_ for _ in ()).throw(ImportError("no cryptography")))
    cred = storage.get_credential()
    assert cred.success is False
    assert cred.cookie is None


def test_credential_result_repr_never_exposes_cookie():
    result = CredentialResult(
        success=True, message="Credential from environment variable", cookie="super-secret-cookie"
    )
    rendered = repr(result)
    assert "super-secret-cookie" not in rendered
    assert "present" in rendered


def test_http_client_builds_cookie_headers_from_env_credential(env_cookie):
    from tp_mcp.client import TPClient

    client = TPClient()
    headers = client._get_cookie_headers(TEST_COOKIE)
    assert headers["Cookie"] == f"Production_tpAuth={TEST_COOKIE}"
    assert TEST_COOKIE not in repr(client)


def test_core_cli_imports_and_reports_missing(monkeypatch, capsys):
    import tp_mcp.auth.storage as storage
    import tp_mcp.core_cli

    assert hasattr(tp_mcp.core_cli, "main")
    monkeypatch.delenv("TP_AUTH_COOKIE", raising=False)
    monkeypatch.setattr(storage, "is_keyring_available", lambda: False)
    monkeypatch.setattr(storage, "_encrypted", lambda: (_ for _ in ()).throw(ImportError("no cryptography")))
    assert tp_mcp.core_cli.main(["auth-status"]) == 1
    assert "No TrainingPeaks credential configured." in capsys.readouterr().out


def test_auth_init_lazy_exports(env_cookie):
    import tp_mcp.auth as auth

    assert callable(auth.get_credential)
    assert callable(auth.validate_auth_sync)
    with pytest.raises(AttributeError):
        _ = auth.does_not_exist


def test_core_cli_surface_is_credential_only():
    from tp_mcp.core_cli import parse_args

    with pytest.raises(SystemExit):
        parse_args(["--help"])
    parsed = parse_args(["auth-status"])
    assert parsed.command == "auth-status"
    parsed = parse_args(["auth-clear"])
    assert parsed.command == "auth-clear"
    with pytest.raises(SystemExit):
        parse_args(["serve"])


def test_readme_documents_env_auth():
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(encoding="utf-8")
    assert "TP_AUTH_COOKIE" in readme
