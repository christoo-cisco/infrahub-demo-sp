# Infrahub-Demo-SP: AI Agent Knowledge Base

## TOP 5 SDK PATTERNS (Priority Understanding)

### 1. **Idempotency via `client.filters()` + Deterministic Keys**
- **Core Rule**: Use `self.client.filters(kind="X", name__value=key, branch=self.branch)` for idempotency checks
- **NOT Query Payloads**: Generators must NOT return objects they create (VRF, interfaces, IPs). Returning them breaks internal `CoreGraphQLQueryGroupUpsert` tracking on re-run → `NodeNotFound` → branch wiped
- **Pattern** (generators/generate_l3vpn.py:61-72):
  ```python
  existing_vrf = await self.client.filters(
      kind="IpamVRF", name__value=vpn_name, branch=self.branch
  )
  if existing_vrf:
      vrf = existing_vrf[0]
  else:
      vrf = await self.client.create(kind="IpamVRF", ...)
      await vrf.save(allow_upsert=True)
  ```

### 2. **Branch Parameter on All Operations**
- Every `client.filters()`, `client.create()`, `client.get()` includes `branch=self.branch` (19+ instances in single file)
- Generators/transforms/checks run on branches; all operations must target same branch

### 3. **`.save(allow_upsert=True)` for All Mutations**
- After `client.create()` or field updates, call `.save(allow_upsert=True)`
- `allow_upsert=True` ensures re-runs don't fail on existing objects
- Missing this breaks idempotency on second runs

### 4. **Pool Allocation with Status in Data**
- Always pass `data={"status": "active"}` to `allocate_next_ip_prefix()`
- `IpamPrefix.status` is required; without it, allocation fails schema validation
- generators/common.py:29 shows the pattern

### 5. **Graceful Unset Relationship Handling**
- Unset relationships return `{"node": None}` (truthy dict, not falsy)
- Always check: `vrf_rel = node.get("vrf") or {}; vrf_node = vrf_rel.get("node"); if not vrf_node: continue`
- checks/l3vpn_overlap.py:22-25 demonstrates this

---

## TOP 5 COMPONENT-SPECIFIC CONVENTIONS

### Generators (generators/*.py)
| Aspect | Pattern |
|--------|---------|
| **Class** | `InfrahubGenerator` |
| **Method** | `async def generate(self, data: dict[str, Any] \| None = None) -> None` |
| **Query Design** | Return source data + input relationships; **NOT** generator-created objects |
| **Idempotency** | Via `client.filters()` + deterministic keys |
| **Error Handling** | Raise `RuntimeError` for missing required data; `LOG.warning()` for non-critical |
| **Examples** | generators/generate_l3vpn.py, generators/generate_sdwan.py |

### Transforms (transforms/*.py)
| Aspect | Pattern |
|--------|---------|
| **Class** | `InfrahubTransform` |
| **Query Ref** | `query = "pe"` (name from `.infrahub.yml`) |
| **Method** | `async def transform(self, data: dict[str, Any]) -> str` |
| **Jinja2 Setup** | **Always**: `autoescape=select_autoescape(disabled_extensions=("j2",), default_for_string=False)` |
| **Return Type** | String (rendered device config) |
| **Examples** | All 9 PE/core/SD-WAN transforms use same Jinja2 pattern |

### Checks (checks/*.py)
| Aspect | Pattern |
|--------|---------|
| **Class** | `InfrahubCheck` |
| **Query Ref** | `query = "l3vpn_overlap"` (name from `.infrahub.yml`) |
| **Method** | `async def validate(self, data: dict[str, Any]) -> None` |
| **Logging** | `self.log_error()` fails check; `self.log_info()` for info only |
| **External Services** | Log once on error, return `None` (prevent double-logging) |
| **Examples** | checks/l3vpn_overlap.py (simple), checks/batfish_backbone.py (complex) |

### Queries (queries/*.gql)
| Type | Pattern |
|------|---------|
| **Generator** (queries/service/*.gql) | Return source + input relationships; omit VRF, interfaces, IPs |
| **Transform** (queries/config/*.gql) | Return device + full nested data (all interfaces, processes) |
| **Validation** (queries/validation/*.gql) | Return minimal data needed for validation (IDs, relationships) |
| **Variable Scoping** | Use parameters (e.g., `$name: String!`) to scope per-operation |

### Streamlit Service Catalog (service_catalog/)
| Pattern | Purpose |
|---------|---------|
| `client_for(branch)` | Create SDK client bound to branch |
| `run_async(coro)` | Run async code from sync Streamlit |
| `prefetch_relationships=True` | Eager-load relationships for UI |
| Validators (pure Python) | No SDK calls in form validation |
| Branch creation → mutations → group membership | Trigger generator via group membership, not form |

---

## TOP 3 PITFALLS (Examples + Fixes)

### Pitfall 1: Returning Generator-Created Objects in Queries ⚠️
**Problem**: If query includes `vrf`, `pe_interface`, `pe_address`, `ce_address` fields, CoreGraphQLQueryGroupUpsert breaks on re-run.

**Bad Example**:
```graphql
query L3Vpn($name: String!) {
  ServiceL3Vpn(name__value: $name) {
    node {
      id
      vrf { node { id } }              # ← BAD! Generator creates this
      sites {
        node {
          pe_interface { node { id } } # ← BAD! Generator creates this
        }
      }
    }
  }
}
```

**Fix** (queries/service/l3vpn.gql):
- Return only ServiceL3Vpn + source relationships (sites, pe_device, customer_subnet)
- Omit all generator-created objects

---

### Pitfall 2: Missing `autoescape=False` in Jinja2 Templates
**Problem**: Device configs with `<`, `&`, `>` characters become HTML entities (`&lt;`, `&amp;`, `&gt;`), breaking device syntax.

**Bad**:
```python
env = Environment(loader=FileSystemLoader(...))  # Default autoescape=True → entities!
```

**Good** (all 9 transforms):
```python
env = Environment(
    loader=FileSystemLoader(...),
    autoescape=select_autoescape(disabled_extensions=("j2",), default_for_string=False),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)
```

---

### Pitfall 3: Forgetting `.save(allow_upsert=True)` on Idempotent Objects
**Problem**: Object updates lose modifications on re-run if `.save()` is skipped.

**Bad**:
```python
iface = await self.client.filters(...)  # Fetches existing
iface.status.value = "active"           # Modified but NOT saved!
```

**Good** (generators/generate_l3vpn.py):
```python
iface = await self.client.filters(...)[0]
iface.status.value = "active"
await iface.save(allow_upsert=True)  # Persist on every run
```

---

## MISSING DOCUMENTATION (Recommend Adding to AGENTS.md)

### Critical Sections to Add:

1. **Generator Query Design Rule**
   - "Generators must NOT return objects they create (VRF, interfaces, IPs)"
   - "Returning created objects breaks CoreGraphQLQueryGroupUpsert on re-run"
   - "Return only source data + input relationships"

2. **Idempotency Pattern Reference**
   - "Use `client.filters()` with deterministic keys, NOT query payloads"
   - "Link to generators/generate_l3vpn.py:61-72 example"

3. **Branch Parameter Requirement**
   - "Every SDK call includes `branch=self.branch`"
   - "Generators/transforms/checks run on branches"

4. **Pool Status Payload Rule**
   - "When allocating prefixes, pass `data={'status': 'active'}`"
   - "IpamPrefix.status is required; without it, allocation fails validation"

5. **Error Handling Strategy**
   - "Generators: raise RuntimeError for missing data"
   - "Checks: log_error() fails check, log_info() for warnings"
   - "External services: single log_error() on failure, return None (prevent double-logging)"
   - "Link to checks/batfish_backbone.py:160-190 example"

6. **Unset Relationship Safety**
   - "Unset relationships return `{'node': None}` (truthy dict, not falsy)"
   - "Must check: `vrf_node = (node.get('vrf') or {}).get('node'); if not vrf_node: continue`"

7. **Transform Query Scope**
   - "All PE transforms use the same 'pe' query from `.infrahub.yml`"
   - "Query returns device + all interfaces/processes for multi-vendor templates"

8. **Streamlit Patterns**
   - "Forms use pure-Python validators (no SDK calls in validators)"
   - "Generators triggered by group membership triggers, not directly in forms"
   - "Use `run_async()` to bridge sync Streamlit ↔ async SDK"

---

## DEBUGGING QUICK-START

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Generator runs once, fails on second run | Missing idempotency keys | Add `client.filters()` checks before `client.create()` |
| Generator runs, creates objects, but misses updates | Missing `.save(allow_upsert=True)` | Add `.save(allow_upsert=True)` after field updates |
| Check fails silently on Batfish timeout | Missing error logging | Add explicit `log_error()` on HTTP failures |
| Device config has HTML entities (`&lt;`) | Jinja2 autoescape enabled | Set `autoescape=False` in Environment setup |
| Query breaks on re-run (CoreGraphQLQueryGroupUpsert error) | Query returns created objects | Remove generator-created fields from query |

---

## FILE MAP: Key Examples by Concept

| Concept | File | Lines | Purpose |
|---------|------|-------|---------|
| Idempotent VRF creation | generators/generate_l3vpn.py | 61-72 | Filter → create → save pattern |
| Pool allocation | generators/common.py | 29 | Status in data parameter |
| Transform template | transforms/pe_arista_eos.py | 17-31 | Jinja2 setup + render |
| Check validation | checks/l3vpn_overlap.py | 14-39 | GraphQL result navigation + logging |
| External service resilience | checks/batfish_backbone.py | 160-190 | HTTP error handling + timeouts |
| Query design | queries/service/l3vpn.gql | - | Omit generator-created objects |
| Streamlit form | service_catalog/pages/1_Create_L3VPN.py | 51-82 | Branch creation + group membership |
| Unit test | tests/unit/test_generators/test_common.py | - | Mock SDK, test idempotency |

