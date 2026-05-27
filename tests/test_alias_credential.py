"""Tests for alias-based credential resolution in the CLI pipeline.

Verifies that when multiple auth bindings share the same host but have
different aliases/credentials, the correct credential is selected based
on the alias used in the URL.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from rub.adapter import ExecutionResult
from rub.auth.binding import AuthBinding, AuthBindings
from rub.auth.profile import AuthType, LiteralSecret, Profile, Profiles
from rub.cli import _run_pipeline


@pytest.fixture
def shared_host_setup(tmp_path):
    """Set up profiles and bindings where two aliases share the same host."""
    bindings_path = tmp_path / "bindings.json"
    creds_path = tmp_path / "creds.json"

    profiles = Profiles(path=creds_path)
    profiles.set_profile(
        Profile(
            name="cred-ws-a",
            auth_type=AuthType.custom,
            secret_source=LiteralSecret(value="token-a"),
        )
    )
    profiles.set_profile(
        Profile(
            name="cred-ws-b",
            auth_type=AuthType.custom,
            secret_source=LiteralSecret(value="token-b"),
        )
    )
    profiles.save()

    bindings = AuthBindings(path=bindings_path)
    bindings._bindings = [
        AuthBinding(
            host="https://api-gateway.example.com",
            credential="cred-ws-a",
            alias="ws-a",
            meta={"workspace": "a"},
        ),
        AuthBinding(
            host="https://api-gateway.example.com",
            credential="cred-ws-b",
            alias="ws-b",
            meta={"workspace": "b"},
        ),
    ]
    bindings.save()

    return bindings_path, creds_path


async def _run_with_alias(shared_host_setup, alias: str, credential: str | None = None):
    """Helper: run _run_pipeline with given alias, capture auth_headers."""
    bindings_path, creds_path = shared_host_setup

    captured: dict[str, Any] = {}

    async def mock_execute(url, op_id, args, *, auth_headers=None):
        captured["headers"] = auth_headers
        captured["args"] = dict(args)
        return ExecutionResult(data={"ok": True}, status_code=200)

    mock_adapter = AsyncMock()
    mock_adapter.execute = mock_execute
    mock_adapter.can_handle = AsyncMock(return_value=True)
    mock_adapter.protocol_name = AsyncMock(return_value="datum")

    mock_registry = AsyncMock()
    mock_registry.detect_protocol = AsyncMock(return_value=mock_adapter)

    mock_framework = AsyncMock()
    mock_framework.registry = mock_registry
    mock_framework.hook = AsyncMock()
    mock_framework.hook.on_before_auth = lambda **kw: None

    # Patch the default paths so AuthBindings() and Profiles() load our fixtures
    with (
        patch("rub.auth.binding._DEFAULT_BINDINGS_PATH", bindings_path),
        patch("rub.auth.profile._DEFAULT_CREDENTIALS_PATH", creds_path),
    ):
        await _run_pipeline(
            mock_framework,
            cache=None,
            url=f"datum://{alias}",
            operation="test.op",
            args={"key": "val"},
            credential=credential,
        )

    return captured


class TestAliasCredentialResolution:
    """Alias resolution must select the correct credential from shared-host bindings."""

    @pytest.mark.asyncio
    async def test_second_alias_uses_its_own_credential(self, shared_host_setup):
        """Using alias 'ws-b' (second in list) should use token-b, not token-a."""
        captured = await _run_with_alias(shared_host_setup, "ws-b")

        assert captured["headers"] == {"Authorization": "token-b"}
        assert captured["args"]["workspace"] == "b"

    @pytest.mark.asyncio
    async def test_first_alias_uses_its_own_credential(self, shared_host_setup):
        """Using alias 'ws-a' (first in list) should use token-a."""
        captured = await _run_with_alias(shared_host_setup, "ws-a")

        assert captured["headers"] == {"Authorization": "token-a"}
        assert captured["args"]["workspace"] == "a"

    @pytest.mark.asyncio
    async def test_explicit_credential_overrides_alias(self, shared_host_setup):
        """Explicit credential (-c flag) takes precedence over alias."""
        captured = await _run_with_alias(
            shared_host_setup, "ws-b", credential="cred-ws-a"
        )

        # Explicit -c wins over alias resolution
        assert captured["headers"] == {"Authorization": "token-a"}
