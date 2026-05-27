# Rub Usage Guide

## Core Interaction Pattern

Rub follows a simple, consistent flow across all protocols:

1. **Discover** — What can this endpoint do?
2. **Inspect** — What does this operation need?
3. **Invoke** — Execute with structured parameters

This pattern stays the same whether you're calling OpenAPI, GraphQL, gRPC, or MCP endpoints.

---

## Example: Multi-Region Echo Service

Let's walk through a realistic scenario: managing multiple regional deployments of an echo service.

### Step 1: Configure Credentials

Each region has its own authentication token:

```bash
rub auth set us-key --secret "us-production-token-xxx"
rub auth set eu-key --secret "eu-production-token-xxx"
rub auth set dev-key --secret "dev-testing-token-xxx"
```

### Step 2: Bind Hosts with Aliases

Map each credential to its host and give it a short alias:

```bash
rub auth bind us-key --host echo-us.example.com --alias us
rub auth bind eu-key --host echo-eu.example.com --alias eu
rub auth bind dev-key --host echo-dev.example.com --alias dev
```

**Alias naming guidelines:**
- ✅ Recommended: `prod`, `us-west`, `api-v2`, `region.eu`
- ❌ Avoid: `region/us` (slashes are URL path separators and won't work as expected)

### Step 3: Discover Operations

Check what each region supports:

```bash
# Discover operations in US region
rub echo://us -h

# Output:
# Available operations:
#   send       Send a message and get echo response
#   broadcast  Broadcast to all connected clients
#   ping       Health check
```

### Step 4: Inspect Operation Details

See what parameters an operation needs:

```bash
rub echo://us send -h

# Output:
# Operation: send
# Description: Send a message and get echo response
# Parameters:
#   message (string, required) — The message to echo
#   timestamp (boolean, optional) — Include timestamp in response
```

### Step 5: Invoke

Call operations using aliases — credentials are automatically applied:

```bash
# Send to US region
rub echo://us send message="Hello from US" timestamp=true

# Send to EU region
rub echo://eu send message="Hello from EU"

# Test in dev environment
rub echo://dev send message="Testing new feature"
```

**No need to:**
- Specify `--credential` each time
- Remember full hostnames
- Switch between auth profiles manually

Rub automatically:
1. Resolves alias (`us` → `echo-us.example.com`)
2. Matches host to binding
3. Loads the correct credential
4. Injects it into the request

---

## URL Patterns and Protocol Detection

Rub supports multiple ways to specify targets, depending on the protocol and use case.

### Pattern 1: Direct Endpoint URL

```bash
rub https://api.example.com/openapi.json -h
rub https://api.example.com/openapi.json getUser id=123
```

**When to use**: For any real API endpoint — OpenAPI schemas, GraphQL endpoints, gRPC services, etc.

**How it works**: Rub fetches the URL, tries each registered adapter's `can_handle()` method in priority order, and the first match wins.

### Pattern 2: Protocol-Specific Scheme with Alias

```bash
rub echo://prod -h
rub echo://prod send message="Hello"
```

**When to use**: 
- **Production workflows**: Use aliases for frequently-accessed hosts
- **Testing/demo**: `echo://` is a built-in test adapter for validating the plugin pipeline
- **Custom protocols**: Adapters can register custom URL schemes (e.g., `mcp://`, `graphql://`) for unambiguous routing

**How it works**: 
1. Rub extracts the hostname part (`prod`)
2. Checks if it's an alias in bindings
3. Resolves to real host (`echo.example.com`)
4. Matches binding to get credential
5. Routes to the appropriate adapter

### Pattern 3: Full URL with Scheme

```bash
rub echo://echo.example.com:7007 -h
rub echo://echo.example.com send message="Hello"
```

**When to use**: When you need to specify the full address (port, path) or the host isn't aliased.

**How it works**: Direct host matching against bindings, no alias resolution.

---

## When to Use Each Pattern

| Pattern | Example | Use Case |
|---------|---------|----------|
| **Alias** | `rub echo://prod send` | Daily operations, frequent calls, multi-environment |
| **Full URL** | `rub echo://api.example.com send` | One-off calls, explicit routing |
| **HTTPS URL** | `rub https://api.example.com/spec getUser` | OpenAPI/REST endpoints with schema discovery |

---

## Multi-Environment Workflow

A typical production setup:

```bash
# One-time setup
rub auth set prod-key --secret "$PROD_TOKEN"
rub auth set staging-key --secret "$STAGING_TOKEN"
rub auth set dev-key --secret "$DEV_TOKEN"

rub auth bind prod-key --host api.example.com --alias prod
rub auth bind staging-key --host api-staging.example.com --alias staging
rub auth bind dev-key --host api-dev.example.com --alias dev

# Daily usage (no auth flags needed)
rub echo://dev send message="Test feature"
rub echo://staging send message="Staging validation"
rub echo://prod send message="Production deployment"
```

---

## Echo Adapter: Two Entry Points

The echo adapter is available in **two ways**:

### 1. Standalone CLI: `echo`

```bash
echo -h                    # Discover operations
echo greet -h              # Inspect greet operation
echo greet name=Meta42     # Invoke greet
```

**When to use**: Direct testing, quick validation, or when you don't need rub's full pipeline (protocol detection, caching, auth).

**How it's registered**: Entry point in `packages/rub-echo/pyproject.toml`:
```toml
[project.scripts]
echo = "rub_echo.__main__:app"
```

### 2. Via Rub: `rub echo://`

```bash
rub echo://test -h
rub echo://test greet name=Meta42
```

**When to use**: When you want the full rub pipeline — caching, auth resolution, hook lifecycle, or when testing multi-protocol detection logic.

**How it's registered**: Entry point in `packages/rub-echo/pyproject.toml`:
```toml
[project.entry-points.'rub.adapters']
echo = "rub_echo.adapter:EchoAdapter"
```

---

## Protocol Detection Priority

Adapters are tried in **descending priority order**:

1. **Built-in adapters** (registered via `RubFramework._register_builtin_adapters()`)
   - `OpenAPIAdapter` (priority: 200)
2. **Entry-point adapters** (registered via `importlib.metadata.entry_points(group="rub.adapters")`)
   - `EchoAdapter` (priority: 50)

Higher priority = tried first. If multiple adapters claim they can handle a URL, the highest-priority one wins.

---

## URL Scheme Best Practices

| Scheme | Recommended Use |
|--------|----------------|
| `https://` | Production APIs, real endpoints |
| `http://` | Local dev servers, insecure endpoints |
| `echo://` | Testing, pipeline validation, multi-region demos |
| Custom (`mcp://`, `graphql://`) | Protocol-specific adapters that want unambiguous routing |

---

## FAQ

### Q: Why use `echo://prod` instead of just `prod`?

The `echo://` prefix makes it clear this is a **network operation** with a specific protocol. It avoids ambiguity with operation names and maintains consistent URL semantics across all adapters.

### Q: Can I skip protocol detection and force a specific adapter?

Not directly via CLI (yet), but you can:
- Use protocol-specific schemes (`echo://`, `mcp://`) to guide detection
- In Python code, instantiate the adapter directly and call methods

### Q: Do I need to configure bindings for every endpoint?

No — bindings are **optional**. You only need them when:
- The endpoint requires authentication
- You want to use a short alias for convenience
- You're managing multiple environments

For public, unauthenticated APIs, just use the full URL directly.

### Q: Can I use wildcard patterns in bindings?

Yes! Bindings support glob patterns:

```bash
rub auth bind shared-key --host "*.example.com"  # Matches all subdomains
rub auth bind api-key --host "api-*.example.com" # Matches api-dev, api-prod, etc.
```

---

## Summary

```bash
# Real endpoints (OpenAPI, GraphQL, etc.)
rub https://api.example.com/spec -h

# Aliased hosts (with auto-auth)
rub echo://prod send message="Hello"

# Full protocol URLs
rub echo://echo.example.com:7007 send message="Hello"

# Standalone echo CLI
echo greet name=Alice
```

Rub's power is in its **unified interface** — the same `rub <target> <operation> key=value` pattern works for any protocol, with adapters handling protocol-specific details transparently.
