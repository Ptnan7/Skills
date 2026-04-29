# Swagger Version Comparison

Before updating AAZ-generated code for a new API version, compare the old and new swagger to understand which APIs changed. This guides what needs to be regenerated and what custom code needs updating.

---

## Quick Diff with Script (Preferred)

Use the automated diff script to compare two API versions. Requires `AAZ_SWAGGER_PATH` (set by `use_aaz_dev_env.ps1`).

```powershell
. .github\cdn-cli\scripts\use_aaz_dev_env.ps1

# Front Door example: compare 2025-10-01 -> 2025-11-01
python .github\cdn-cli\scripts\swagger_diff.py --ext front-door --old 2025-10-01 --new 2025-11-01

# CDN example: compare 2024-02-01 -> 2025-09-01-preview
python .github\cdn-cli\scripts\swagger_diff.py --ext cdn --old 2024-02-01 --new 2025-09-01-preview
```

The script:
1. Parses the swagger `readme.md` to map version → tag → input files
2. Loads and merges all JSON files for each tag
3. Compares operations, models, enums, and parameters
4. Reports added/removed/modified items and flags breaking changes
5. Prints a resource-level planning list: updated APIs, new APIs, and normalized AddSwagger resource candidates

**Wait for the user to acknowledge the diff** before proceeding with AAZ generation or code changes.

---

## Locate the Current Version

Read `.Autorest/README.md` (for PowerShell) or check the existing AAZ files at `azext_cdn/aaz/latest/` to identify the API version currently in use (e.g. `2024-02-01`, `stable` or `preview`).

For CLI extensions, grep for `api-version` in the AAZ-generated Python files:

```powershell
Get-ChildItem -Path "$env:AAZ_CLI_EXTENSION_PATH\src\front-door\azext_front_door\aaz\latest\" -Recurse -Filter "*.py" |
  Select-String -Pattern "api-version" |
  Select-Object -Property Line -Unique
```

---

## Manual Diff (Alternative)

If the script is not available, compare manually:

### Swagger Source Paths

| Extension | Spec directory under `azure-rest-api-specs` |
|-----------|---------------------------------------------|
| CDN / AFD | `specification/cdn/resource-manager/Microsoft.Cdn/Cdn/` |
| Front Door | `specification/frontdoor/resource-manager/Microsoft.Network/FrontDoor/` |

Files are at `<spec-dir>/<stable|preview>/<version>/openapi.json` (or `network.json`, `webapplicationfirewall.json` for older multi-file tags).

### Focus Areas

| Area | What to look for |
|------|-----------------|
| `paths` | New, removed, or renamed operations (HTTP method + path) |
| `definitions` / `components/schemas` | New or removed models, renamed properties, changed types, new required fields |
| `parameters` | New or removed query/path/body parameters on existing operations |
| `x-ms-enum` | New enum values or renamed members |

### Summarize the Diff

Present before touching any code:

1. New operations (resource type + HTTP verb)
2. Removed operations
3. Modified operations (parameter changes, response shape changes)
4. New or removed top-level models
5. Breaking changes (removed required fields, renamed enum values, removed operations)
6. AddSwagger resource candidates from updated and new APIs

**Wait for the user to acknowledge the diff** before proceeding with AAZ generation or code changes.

---

## CLI-Specific Follow-up

After reviewing the diff, identify which parts of the CLI extension need attention:

| Change type | What to check in the extension |
|-------------|-------------------------------|
| New operation | Re-run `aaz-dev` to generate a new command; register in `commands.py` |
| Removed operation | Remove the command from `commands.py`; remove custom code if any |
| New required parameter | Update custom subclasses in `custom/` that set defaults or hide args |
| Renamed property | Update `_params.py` completer/validator references and `_help.py` examples |
| New enum value | AAZ re-generation picks it up automatically; verify `_help.py` examples |
| Breaking change | Flag to the user — may require a version bump or deprecation notice |
