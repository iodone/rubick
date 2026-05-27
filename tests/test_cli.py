"""CLI integration tests using typer.testing.CliRunner."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from rub.cli import app

runner = CliRunner()


class TestRubHelp:
    """Test rub --help output."""

    def test_help_flag(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Universal API CLI" in result.output
        assert "discover" in result.output.lower() or "invoke" in result.output.lower()

    def test_help_shows_subcommands(self):
        result = runner.invoke(app, ["--help"])
        assert "auth" in result.output
        assert "cache" in result.output


class TestAuthCLI:
    """Test rub auth subcommands."""

    def test_auth_help(self):
        result = runner.invoke(app, ["auth", "--help"])
        assert result.exit_code == 0
        assert "auth" in result.output.lower()

    def test_auth_list_empty(self, tmp_path):
        """auth list with no profiles configured."""
        tmp_path / "creds.json"
        with patch("rub.auth.cli.Profiles") as MockProfiles:
            instance = MockProfiles.return_value
            instance.load.return_value = None
            instance.list_profiles.return_value = []
            result = runner.invoke(app, ["auth", "list"])
            assert result.exit_code == 0
            assert "No profiles" in result.output

    def test_auth_set_requires_secret_or_env(self):
        """auth set without --secret or --env should fail."""
        with patch("rub.auth.cli.Profiles") as MockProfiles:
            instance = MockProfiles.return_value
            instance.load.return_value = None
            result = runner.invoke(app, ["auth", "set", "myprofile"])
            assert result.exit_code != 0


class TestCacheCLI:
    """Test rub cache subcommands."""

    def test_cache_help(self):
        result = runner.invoke(app, ["cache", "--help"])
        assert result.exit_code == 0
        assert "cache" in result.output.lower()

    def test_cache_stats(self, tmp_path):
        """cache stats shows entry counts."""

        with patch("rub.cache_cli.RubSettings") as MockSettings:
            MockSettings.return_value.cache_db_path = tmp_path / "cache.db"
            result = runner.invoke(app, ["cache", "stats"])
            assert result.exit_code == 0
            assert "Total entries" in result.output
            assert "Active entries" in result.output
            assert "Expired entries" in result.output

    def test_cache_clear(self, tmp_path):
        """cache clear empties the cache."""
        with patch("rub.cache_cli.RubSettings") as MockSettings:
            MockSettings.return_value.cache_db_path = tmp_path / "cache.db"
            # First populate something
            result = runner.invoke(app, ["cache", "clear"])
            assert result.exit_code == 0
            assert "Cleared" in result.output


class TestMainCallback:
    """Test the main callback behavior."""

    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        # no_args_is_help=True causes Click to exit with code 0 or 2
        assert result.exit_code in (0, 2)
        assert "Usage" in result.output or "rub" in result.output


@pytest.mark.asyncio
class TestRequiredParameterValidation:
    async def test_missing_required_param_returns_error(self):
        from conftest import MockAdapter

        from rub.pipeline import run_pipeline
        from rub.schema import Operation, Parameter

        adapter = MockAdapter(
            operations=[
                Operation(
                    operation_id="needs",
                    display_name="Needs",
                    description="",
                    parameters=[
                        Parameter(name="x", param_type="string", required=True)
                    ],
                )
            ]
        )

        envelope = await run_pipeline(
            adapter, "mock://test", "needs", {}, api_help=False
        )
        assert envelope.ok is False
        assert envelope.error_info is not None
        assert envelope.error_info.code == "MISSING_REQUIRED_PARAMS"
        assert envelope.error_info.details is not None
        assert "x" in envelope.error_info.details

    async def test_none_counts_as_missing_but_empty_string_does_not(self):
        from conftest import MockAdapter

        from rub.pipeline import run_pipeline
        from rub.schema import Operation, Parameter

        adapter = MockAdapter(
            operations=[
                Operation(
                    operation_id="needs",
                    display_name="Needs",
                    description="",
                    parameters=[
                        Parameter(name="x", param_type="string", required=True)
                    ],
                )
            ]
        )

        env_none = await run_pipeline(
            adapter, "mock://test", "needs", {"x": None}, api_help=False
        )
        assert env_none.ok is False
        assert env_none.error_info is not None
        assert env_none.error_info.code == "MISSING_REQUIRED_PARAMS"

        env_empty = await run_pipeline(
            adapter, "mock://test", "needs", {"x": ""}, api_help=False
        )
        assert env_empty.ok is True

    async def test_default_is_applied_before_required_check(self):
        from conftest import MockAdapter

        from rub.pipeline import run_pipeline
        from rub.schema import Operation, Parameter

        adapter = MockAdapter(
            operations=[
                Operation(
                    operation_id="needs",
                    display_name="Needs",
                    description="",
                    parameters=[
                        Parameter(
                            name="x", param_type="string", required=True, default="ok"
                        )
                    ],
                )
            ]
        )

        envelope = await run_pipeline(
            adapter, "mock://test", "needs", {}, api_help=False
        )
        assert envelope.ok is True
