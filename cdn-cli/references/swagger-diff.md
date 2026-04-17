# Swagger Version Comparison

Before updating AAZ-generated code for a new API version, compare the old and new swagger to understand which APIs changed. This guides what needs to be regenerated and what custom code needs updating.

---

## Locate the Current Version

Read `.Autorest/README.md` (for PowerShell) or check the existing AAZ files at `azext_cdn/aaz/latest/` to identify the API version currently in use (e.g. `2024-02-01`, `stable` or `preview`).

---

## Determine the Swagger Source

Ask the user if not already stated:

- **Local clone** — the user has a local clone of `azure-rest-api-specs`. Ask for the repo root path (e.g. `C:\repos\azure-rest-api-specs`). The swagger file is at:
  `<repo-root>/specification/cdn/resource-manager/Microsoft.Cdn/Cdn/<stable|preview>/<version>/openapi.json`

- **GitHub** — read directly from GitHub:

  | Channel | Browsable URL |
  |---------|--------------|
  | stable  | `https://github.com/Azure/azure-rest-api-specs/blob/main/specification/cdn/resource-manager/Microsoft.Cdn/Cdn/stable/<version>/openapi.json` |
  | preview | `https://github.com/Azure/azure-rest-api-specs/blob/main/specification/cdn/resource-manager/Microsoft.Cdn/Cdn/preview/<version>/openapi.json` |

  Fetch raw content via:
  `https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/specification/cdn/resource-manager/Microsoft.Cdn/Cdn/<stable|preview>/<version>/openapi.json`

For the old version, use whichever source is available. Mixed scenarios (e.g. old from GitHub, new from local) are fine.

---

## Diff the Two `openapi.json` Files

Focus on these areas:

| Area | What to look for |
|------|-----------------|
| `paths` | New, removed, or renamed operations (HTTP method + path) |
| `definitions` / `components/schemas` | New or removed models, renamed properties, changed types, new required fields |
| `parameters` | New or removed query/path/body parameters on existing operations |
| `x-ms-enum` | New enum values or renamed members |

---

## Summarize the Diff

Present before touching any code:

1. New operations (resource type + HTTP verb)
2. Removed operations
3. Modified operations (parameter changes, response shape changes)
4. New or removed top-level models
5. Breaking changes (removed required fields, renamed enum values, removed operations)

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
