"""Standalone CLI generator for individual adapters.

Allows any adapter to become its own independent CLI with full
discover → inspect → invoke pipeline, without going through rub's
protocol detection layer.

Usage in an adapter package::

    # rub_echo/__main__.py
    from rub.standalone import standalone_cli
    from rub_echo.adapter import EchoAdapter

    app = standalone_cli(EchoAdapter(), name="echo")

    if __name__ == "__main__":
        app()
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import click
import typer

from rub.adapter import Adapter
from rub.envelope import OutputEnvelope
from rub.formatter import emit_rich
from rub.pipeline import run_pipeline


def _parse_key_value(raw: str) -> tuple[str, Any]:
    """Parse key=value or key:=json."""
    if ":=" in raw:
        key, _, json_str = raw.partition(":=")
        if not key:
            raise typer.BadParameter(f"Empty key in argument: {raw!r}")
        try:
            value = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(
                f"Invalid JSON after ':=' in {raw!r}: {exc}"
            ) from exc
        return key, value
    if "=" not in raw:
        raise typer.BadParameter(f"Argument must be key=value, got: {raw!r}")
    key, _, value = raw.partition("=")
    if not key:
        raise typer.BadParameter(f"Empty key in argument: {raw!r}")
    return key, value


def _set_nested(d: dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    current = d
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def _build_args(kv_args: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for raw in kv_args:
        key, value = _parse_key_value(raw)
        _set_nested(result, key, value)
    return result


def _emit(envelope: OutputEnvelope, *, fmt: str = "json") -> None:
    if fmt == "table":
        emit_rich(envelope)
    elif fmt == "text":
        if envelope.ok:
            if envelope.data is not None:
                if isinstance(envelope.data, (dict, list)):
                    typer.echo(json.dumps(envelope.data, indent=2))
                else:
                    typer.echo(str(envelope.data))
        else:
            err = envelope.error_info
            msg = err.message if err else "Unknown error"
            typer.echo(f"Error [{err.code if err else 'UNKNOWN'}]: {msg}", err=True)
    else:
        typer.echo(envelope.model_dump_json(indent=2, exclude_none=True))


class _StandaloneGroup(typer.core.TyperGroup):
    """Click group that intercepts -h and treats all args as belonging
    to the default callback command (no subcommand routing).

    This lets ``echo -h`` trigger discovery and ``echo greet -h``
    trigger inspect, rather than Click consuming -h as a help flag.
    It also ensures single-segment names like ``finance`` are passed
    as the ``operation`` argument instead of being rejected as
    "No such command".
    """

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        # Extract -h from args before Click sees it
        if "-h" in args:
            args = [a for a in args if a != "-h"]
            ctx.ensure_object(dict)
            ctx.obj["api_help"] = True
        else:
            ctx.ensure_object(dict)
            ctx.obj["api_help"] = False
        return super().parse_args(ctx, args)

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        # Always route to the default (callback) command — do not
        # try to interpret the first arg as a subcommand name.
        cmd_name = self.name
        cmd = self.commands.get(cmd_name)
        if cmd is not None:
            return cmd_name, cmd, args
        return super().resolve_command(ctx, args)


def standalone_cli(
    adapter: Adapter,
    *,
    name: str | None = None,
    default_url: str | None = None,
) -> typer.Typer:
    """Generate a standalone Typer CLI for a single adapter.

    The generated CLI has the same discover → inspect → invoke pipeline
    as ``rub``, but skips protocol detection (adapter is known).

    Args:
        adapter: An instantiated Adapter.
        name: CLI name (used in help text and examples).
        default_url: Default URL when the adapter doesn't need one.
    """
    cli_name = name or "adapter"
    _default_url = default_url or f"{cli_name}://default"

    app = typer.Typer(
        name=cli_name,
        cls=_StandaloneGroup,
        help=(
            f"{cli_name} — standalone API CLI.\n\n"
            f"Usage:\n\n"
            f"  {cli_name} -h                     Discover operations\n\n"
            f"  {cli_name} <operation> -h          Inspect an operation\n\n"
            f"  {cli_name} <operation> key=value   Invoke with arguments"
        ),
        add_completion=False,
        invoke_without_command=True,
        no_args_is_help=False,
        context_settings={"help_option_names": ["--help"]},
    )

    @app.callback()  # type: ignore[arg-type]
    def main(
        ctx: typer.Context,
        operation: str | None = typer.Argument(
            None, help="Operation to inspect or invoke"
        ),
        args: list[str] | None = typer.Argument(None, help="key=value arguments"),
        url: str = typer.Option(
            _default_url,
            "--url",
            "-u",
            help="Target URL",
        ),
        format: str = typer.Option(
            "json", "--format", "-f", help="Output format: json, table, text"
        ),
        no_cache: bool = typer.Option(False, "--no-cache", help="Bypass schema cache"),
    ) -> None:
        api_help = ctx.obj.get("api_help", False)

        # No operation and no -h → show help
        if operation is None and not api_help:
            typer.echo(ctx.get_help())
            raise typer.Exit()

        if api_help and format == "json":
            format = "table"

        kv_dict = _build_args(args or [])

        async def _run() -> OutputEnvelope:
            from rub.cache import SchemaCache
            from rub.config import RubSettings

            settings = RubSettings()
            cache: SchemaCache | None = None
            if not no_cache:
                db_path = settings.cache_db_path
                db_path.parent.mkdir(parents=True, exist_ok=True)
                cache = SchemaCache(db_path=str(db_path))
                await cache.initialize()

            try:
                return await run_pipeline(
                    adapter,
                    url,
                    operation,
                    kv_dict,
                    api_help=api_help,
                    cache=cache,
                    ttl=settings.cache_ttl,
                    cli_name=cli_name,
                )
            finally:
                if cache is not None:
                    await cache.close()

        envelope = asyncio.run(_run())
        _emit(envelope, fmt=format)

        if not envelope.ok:
            raise typer.Exit(code=1)

    return app
