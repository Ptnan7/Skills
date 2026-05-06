# Front Door Legacy Files And Tests

## Symptom

Front Door work appears to require changes under legacy files, or legacy scenario tests fail during validation.

Common legacy areas:

- `custom.py`
- `custom_waf.py`
- `vendored_sdks/`
- `commands.py`
- `_params.py`
- `_help.py`
- legacy tests for backend pools, frontend endpoints, routing rules, probes, and rules engine

## Rule

For `src/front-door`, only the AAZ-generated subtree is actively maintained:

```text
src/front-door/azext_front_door/aaz/latest/network/front_door/
```

The maintained command surface is primarily `az network front-door waf-policy`.

Do not route fixes through the legacy files. If a legacy file appears to need a fix, route the change through the AAZ-generated path or record it as a known limitation.

## Tests

Run maintained Front Door WAF tests:

```powershell
azdev test test_waf_scenarios
azdev linter front-door
```

Do not treat legacy front-door test failures as blockers for AAZ WAF work unless the task explicitly targets those legacy commands.

When committing recordings, do not commit legacy test recordings such as backend-pool, frontend-endpoint, routing-rule, probe, or rules-engine recordings.
