# AGENTS.md

> Universal guidance for AI coding assistants working in this repository.
> See also: [CLAUDE.md](./CLAUDE.md) for Claude-specific detailed instructions.

## Project Overview

**infrahub-demo-sp** is a comprehensive demonstration of multi-vendor MPLS network provisioning using [Infrahub](https://docs.infrahub.app). It showcases:

- Multi-vendor MPLS backbone topology (Arista EOS, Cisco IOS-XR, Juniper Junos, Nokia SR OS)
- L3VPN service provisioning via Streamlit Service Catalog
- Containerlab lab artifact generation for testing
- Configuration management with Jinja2 templates
- Validation checks for MPLS network devices
- Infrastructure-as-code patterns

## Quick Start

```bash
# Install dependencies
uv sync

# Start Infrahub containers
uv run invoke start

# Bootstrap schemas, menu, and data
uv run invoke bootstrap

# Run full initialization (destroy + start + bootstrap + demo)
uv run invoke init
```

## Build and Test Commands

```bash
# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -vv

# Run specific test categories
uv run pytest tests/unit/
uv run pytest tests/integration/

# Lint and type check
uv run invoke lint         # Full suite: ruff, mypy, yamllint
uv run ruff check . --fix  # Format and lint
uv run mypy .              # Type checking only
```

## Code Style Guidelines

### Python

- **Type hints required** on all function signatures
- **Docstrings required** for all modules, classes, and functions (Google-style)
- Format with `ruff`, pass `mypy` type checking
- PascalCase for classes, snake_case for functions/variables
- Max line length: 100 characters
- Use `pathlib` over `os.path`

### Naming Conventions

- **Schema Nodes**: PascalCase (`LocationBuilding`, `DcimDevice`)
- **Attributes/Relationships**: snake_case (`device_type`, `parent_location`)
- **Namespaces**: PascalCase (`Dcim`, `Ipam`, `Service`, `Design`)

## Architecture Overview

This project follows Infrahub's SDK pattern with five core component types:

```text
schemas/      → Data models, relationships, constraints
generators/   → Create infrastructure topology programmatically
transforms/   → Convert Infrahub data to device configurations
checks/       → Validate configurations and connectivity
templates/    → Jinja2 templates for device configurations
```

### Data Flow

```text
Schema Definition → Data Loading → Generator Execution → Transform Processing → Configuration Generation
                                         ↓
                                   Validation Checks
```

## SDK Essentials (CRITICAL)

Understand these patterns before working on generators/transforms/checks:

### Idempotency via `client.filters()` + Deterministic Keys
- **Core Rule**: Use `self.client.filters(kind="X", name__value=key, branch=self.branch)` for idempotency checks
- **NOT Query Payloads**: Generators must NOT return objects they create (VRF, interfaces, IPs). Returning them breaks `CoreGraphQLQueryGroupUpsert` tracking on re-run → `NodeNotFound` → branch wiped. See [generators/generate_l3vpn.py](generators/generate_l3vpn.py#L61) for correct pattern.

### Branch Parameter on All Operations
- Every `client.filters()`, `client.create()`, `client.get()` includes `branch=self.branch`
- Generators/transforms/checks run on branches; all SDK calls must target same branch

### `.save(allow_upsert=True)` for All Mutations
- After `client.create()` or field updates, always call `.save(allow_upsert=True)`
- Ensures re-runs don't fail on existing objects

### Pool Allocation with Status
- Always pass `data={"status": "active"}` when allocating prefixes
- `IpamPrefix.status` is required by schema. See [generators/common.py](generators/common.py) for pattern.

### Graceful Unset Relationship Handling
- Unset relationships return `{"node": None}` (truthy dict, not falsy)
- Always check: `rel = (node.get("field") or {}).get("node"); if not rel: continue`
- See [checks/l3vpn_overlap.py](checks/l3vpn_overlap.py#L22) for example.

### Key Files

- `.infrahub.yml` - Central registry for all components (transforms, generators, checks, queries)
- `tasks.py` - Invoke task definitions for automation
- `pyproject.toml` - Project dependencies and tool configuration
- [CODEBASE_PATTERNS.md](CODEBASE_PATTERNS.md) - Detailed AI agent knowledge base with examples and pitfalls

## Component-Specific Conventions

### Generators (`generators/*.py`)
- **Class**: Extend `InfrahubGenerator`
- **Method Signature**: `async def generate(self, data: dict[str, Any] | None = None) -> None`
- **Query Design**: Return source data + input relationships; omit VRF, interfaces, IPs that generator creates
- **Idempotency**: Use `client.filters()` with deterministic keys, NOT query payloads
- **Error Handling**: Raise `RuntimeError` for missing required data; `LOG.warning()` for non-critical issues
- **Examples**: [generators/generate_l3vpn.py](generators/generate_l3vpn.py), [generators/generate_sdwan.py](generators/generate_sdwan.py)

### Transforms (`transforms/*.py`)
- **Class**: Extend `InfrahubTransform`
- **Query Reference**: `query = "pe"` (name from `.infrahub.yml` transforms section)
- **Method Signature**: `async def transform(self, data: dict[str, Any]) -> str`
- **Jinja2 Setup** (CRITICAL): Always use `autoescape=select_autoescape(disabled_extensions=("j2",), default_for_string=False)` to prevent `<`, `&`, `>` becoming HTML entities
- **Return Value**: String (rendered device configuration)
- **Examples**: All 9 PE/core/SD-WAN transforms share identical Jinja2 pattern

### Checks (`checks/*.py`)
- **Class**: Extend `InfrahubCheck`
- **Query Reference**: `query = "l3vpn_overlap"` (name from `.infrahub.yml` checks section)
- **Method Signature**: `async def validate(self, data: dict[str, Any]) -> None`
- **Logging**: Use `self.log_error()` to fail check; `self.log_info()` for informational messages
- **External Services**: Log once on error, return `None` (prevents double-logging)
- **Examples**: [checks/l3vpn_overlap.py](checks/l3vpn_overlap.py) (simple), [checks/batfish_backbone.py](checks/batfish_backbone.py) (complex)

### Queries (`queries/*.gql`)
- **Generator Queries**: Return source data + input relationships; omit generated objects (breaks CoreGraphQLQueryGroupUpsert)
- **Transform Queries**: Return device + full nested data (interfaces, processes, addresses)
- **Validation Queries**: Return minimal data needed for checks (IDs, relationships)
- **Variable Scoping**: Use parameters (e.g., `$name: String!`) to scope per-operation

## Testing Instructions

1. **Before committing**: Run `uv run pytest` to ensure all tests pass
2. **For new features**: Add tests in `tests/unit/` or `tests/integration/`
3. **Use mocks**: Mock external dependencies with `unittest.mock`
4. **Test both paths**: Cover success and failure scenarios
5. **Integration tests**: Require running Infrahub instance

## Post-Change Validation

**IMPORTANT**: After making code changes, always run the full lint suite:

```bash
uv run invoke lint  # Runs: ruff, mypy, yamllint
```

This ensures:

- Python code passes ruff linting
- Type hints are correct (mypy)
- YAML files are valid

## Security Considerations

- Never commit `.env` files or credentials
- API tokens in documentation are demo tokens for local development only
- Avoid introducing OWASP top 10 vulnerabilities (XSS, SQL injection, command injection)
- Validate external inputs at system boundaries

## PR and Commit Guidelines

- Use descriptive commit messages focusing on "why" not "what"
- Reference issue numbers where applicable
- Do not auto-commit - only commit when explicitly requested
- **Always run `uv run invoke lint` after code changes and before commits/PRs**

## Development Environment

- **Package Manager**: `uv` (required)
- **Python Version**: 3.10, 3.11, or 3.12
- **Container Runtime**: Docker (for Infrahub)

### Environment Variables

Required in `.env`:

```bash
INFRAHUB_ADDRESS="http://localhost:8000"
INFRAHUB_API_TOKEN="<your-token>"
```

Optional:

```bash
INFRAHUB_GIT_LOCAL="true"  # Use local repo instead of GitHub
```

## Common Pitfalls

1. **Missing `uv sync`** - Always run after pulling changes
2. **Missing type hints** - All functions require complete annotations
3. **Jinja2 autoescape** - Set `autoescape=select_autoescape(disabled_extensions=("j2",), default_for_string=False)` to prevent HTML entity escaping in device configs
4. **HTML entities** - Use `get_interface_roles()` which handles HTML decoding
5. **Missing `.infrahub.yml` entries** - Register all generators/transforms/checks
6. **Wrong box style in Rich** - Use `box.SIMPLE` for terminal compatibility
7. **Query Returns Generator-Created Objects** - If generator query includes VRF/interfaces/IPs that generator creates, `CoreGraphQLQueryGroupUpsert` breaks on re-run with `NodeNotFound`. Always omit generated fields from generator queries.
8. **Forgetting `.save(allow_upsert=True)`** - Object mutations are lost on re-runs without `allow_upsert=True`
9. **Missing Branch Parameter** - Every SDK call (`client.filters()`, `client.create()`, `client.get()`) must include `branch=self.branch`
10. **Unsafe Unset Relationship Checks** - Unset relationships return `{"node": None}` (truthy dict). Must check: `if not (node.get("field") or {}).get("node"): continue`

## Sub-Project Guidelines

- [docs/AGENTS.md](./docs/AGENTS.md) - Documentation site (Docusaurus)

## Resources

- [Infrahub Documentation](https://docs.infrahub.app)
- [Infrahub SDK Documentation](https://docs.infrahub.app/python-sdk/)
- [CLAUDE.md](./CLAUDE.md) - Detailed Claude Code instructions
