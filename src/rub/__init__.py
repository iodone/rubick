"""Rub — Universal API CLI."""

from __future__ import annotations

__version__ = "1.0.0"

import importlib.metadata

import pluggy
from loguru import logger

from rub.adapter import Adapter
from rub.discovery import AdapterRegistry
from rub.envelope import OutputEnvelope
from rub.hooks import RubHookSpecs, hookimpl
from rub.schema import Operation, OperationDetail, Parameter


class RubFramework:
    """Central framework instance that wires pluggy hooks and adapter discovery.

    Initializes the pluggy plugin manager, registers the hook specifications,
    scans entry-point plugins from the ``rub.adapters`` group, and exposes
    the hook caller for lifecycle events.
    """

    def __init__(self) -> None:
        self.pm = pluggy.PluginManager("rub")
        self.pm.add_hookspecs(RubHookSpecs)
        self._load_entry_point_plugins()
        self.registry = AdapterRegistry(plugin_manager=self.pm)
        self._register_builtin_adapters()

    def _register_builtin_adapters(self) -> None:
        """Register built-in adapters that ship with rub core."""
        from rub.adapters import OpenAPIAdapter

        self.registry.register_adapter(OpenAPIAdapter())

    def _load_entry_point_plugins(self) -> None:
        """Load plugins from the ``rub.adapters`` entry-point group.

        Iterates over ``importlib.metadata.entry_points(group='rub.adapters')``
        and registers each loaded object as a pluggy plugin (if it exposes hooks).
        """
        eps = importlib.metadata.entry_points(group="rub.adapters")
        for ep in eps:
            try:
                plugin = ep.load()
                if not self.pm.is_registered(plugin):
                    self.pm.register(plugin, name=ep.name)
                    logger.info("Registered plugin from entry point: %s", ep.name)
            except Exception:
                logger.exception("Failed to load plugin from entry point: %s", ep.name)

    @property
    def hook(self) -> pluggy.HookCaller:
        """Access the pluggy hook caller for firing lifecycle events."""
        return self.pm.hook  # type: ignore[return-value]

    def register_plugin(self, plugin: object) -> None:
        """Register an additional plugin with the plugin manager."""
        self.pm.register(plugin)

    async def get_adapter(self, url: str) -> Adapter:
        """Detect and return the adapter for a URL via the discovery cascade."""
        return await self.registry.get_adapter(url)


# Convenience alias
Rub = RubFramework

from rub.adapters import OpenAPIAdapter
from rub.standalone import standalone_cli

__all__ = [
    "Adapter",
    "AdapterRegistry",
    "OpenAPIAdapter",
    "Operation",
    "OperationDetail",
    "OutputEnvelope",
    "Parameter",
    "Rub",
    "RubFramework",
    "hookimpl",
    "standalone_cli",
]
