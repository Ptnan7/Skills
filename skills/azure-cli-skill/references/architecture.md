# Architecture

## Extensions Overview

| Extension | Package | Commands | Model |
|-----------|---------|----------|-------|
| `src/cdn` | `azext_cdn` | `az cdn ...`, `az afd ...` | Fully AAZ-driven, `azure-mgmt-cdn` |
| `src/front-door` | `azext_front_door` | `az network front-door ...` | Legacy extension; only `aaz/latest/network/front_door/` is actively maintained |

---

## `src/cdn` Project Structure

```
src/cdn/
├── setup.py
├── linter_exclusions.yml
└── azext_cdn/
    ├── __init__.py              # Extension entry point
    ├── commands.py              # Command table registration
    ├── _params.py               # Argument definitions
    ├── _help.py                 # Help text
    ├── _validators.py
    ├── _actions.py
    ├── _client_factory.py       # cf_cdn, cf_endpoints, cf_custom_domain …
    ├── azext_metadata.json
    ├── aaz/latest/
    │   ├── cdn/                 # CDN AAZ commands
    │   └── afd/                 # AFD AAZ commands
    ├── custom/
    │   ├── custom.py            # Legacy CDN SDK-based commands
    │   ├── custom_cdn.py        # CDN AAZ subclasses
    │   ├── custom_afdx.py       # AFD AAZ subclasses
    │   ├── custom_rule_util.py  # Rule condition/action helpers
    │   └── custom_waf.py
    └── tests/latest/
        ├── scenario_mixin.py
        ├── afdx_scenario_mixin.py
        └── recordings/
```

**SDK**: `azure-mgmt-cdn` (CdnManagementClient)  
**Framework**: `azure.cli.core.aaz` + custom AAZ subclasses

---

## `src/front-door` Project Structure (maintained portions only)

```
src/front-door/
└── azext_front_door/
    ├── aaz/latest/network/front_door/   # Only part actively maintained
    │   └── waf_policy/                  # WAF policy CRUD and subresources
    └── tests/latest/                    # Only WAF-related tests maintained
```

All other files (`custom.py`, `custom_waf.py`, `vendored_sdks/`, `commands.py`, `_params.py`, `_help.py`) are legacy and not maintained.

---

## Command Groups

### `az cdn` (in `src/cdn`)

- `cdn profile` — CRUD + migration
- `cdn endpoint` — CRUD, purge, load, start, stop, delivery rules
- `cdn endpoint rule condition / action`
- `cdn origin` / `cdn origin-group`
- `cdn custom-domain` — enable/disable HTTPS
- `cdn name-exists`, `cdn edge-node`
- `cdn waf policy`
- `cdn profile-migration`

### `az afd` (in `src/cdn`)

- `afd profile` — CRUD, log scrubbing
- `afd endpoint`, `afd origin`, `afd origin-group`
- `afd route`, `afd rule`, `afd rule condition/action`
- `afd custom-domain`, `afd secret`
- `afd security-policy`, `afd log-analytic`

### `az network front-door` (in `src/front-door`)

- `network front-door waf-policy` — maintained via AAZ (create, update, delete, show, list, managed rules, custom rules, exclusions)
- All other classic front-door commands (`backend-pool`, `frontend-endpoint`, `probe`, `routing-rule`, `rules-engine`, etc.) are legacy and not maintained
