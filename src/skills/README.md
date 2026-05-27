# Skills Directory

This is a namespace package directory for Rub skill plugins.

Skill packages are installed separately (e.g., `pip install rub-openapi`) and discovered
automatically via Python entry points. Each skill provides a protocol adapter that Rub
uses to discover, inspect, and invoke API operations.

## How it works

Skill packages register themselves in their `pyproject.toml`:

```toml
[project.entry-points."rub.adapters"]
openapi = "rub_openapi:OpenAPIAdapter"
```

Rub scans `importlib.metadata.entry_points(group="rub.adapters")` at runtime to find
all installed adapters. No configuration needed — install the package and it's available.

## Creating a skill

See the plugin development guide for step-by-step instructions on creating a new
protocol adapter.
