# Swagger Version Comparison

Before updating a module, compare the old and new swagger to understand which APIs changed. This guides what needs to be regenerated and what custom code may need updating.

---

## Quick Diff with Script (Preferred)

Use the shared diff script (from `cdn-cli`). Requires `AAZ_SWAGGER_PATH` (set by `use_pwsh_env.ps1`).

```powershell
. .github\cdn-pwsh\scripts\use_pwsh_env.ps1

# CDN / AFD module
python .github\cdn-cli\scripts\swagger_diff.py --ext cdn --old <old-version> --new <new-version>

# Front Door WAF (if needed)
python .github\cdn-cli\scripts\swagger_diff.py --ext front-door --old <old-version> --new <new-version>
```

The script parses the swagger `readme.md`, loads all JSON files for each tag, and reports:
- New/removed/modified operations
- New/removed/modified models and properties
- Enum value changes
- Breaking changes summary

**Wait for the user to acknowledge the diff** before proceeding with code changes.

---

## Locate the Current Version

Read the module's `.Autorest/README.md` and extract:
- The existing API version string (e.g. `2024-02-01`)
- Whether it is `stable` or `preview`

```powershell
Select-String -Path "$env:PWSH_REPO_PATH\src\Cdn\Cdn.Autorest\README.md" -Pattern "api-version|stable/|preview/"
```

---

## Manual Diff (Alternative)

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

**Wait for the user to acknowledge the diff** before proceeding with code changes.

---

## PowerShell-Specific Follow-up

After reviewing the diff, identify which parts of the module need attention:

| Change type | What to check in the module |
|-------------|----------------------------|
| New operation | Will appear in `exports/` after re-generation; needs a new `.Tests.ps1` |
| Removed operation | Remove the orphaned `.Tests.ps1` and `.Recording.json` from `test/` |
| New required parameter | Check `custom/` scripts that call the generated cmdlet internally |
| Renamed model/property | Update `no-inline` and `model-cmdlet` directives in `README.md` |
| New enum value | AutoRest picks it up automatically; verify `examples/` docs still make sense |
| Breaking change | Flag to the user — may require a `README.md` directive to hide/rename |
