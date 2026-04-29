# Architecture

## Repository

The CDN PowerShell module lives in the `azure-powershell` repo, cloned as `pwsh` by the init script. Use `$env:PWSH_REPO_PATH` (set by `use_pwsh_env.ps1`) to reference it. The AutoRest project is at:

```
$env:PWSH_REPO_PATH\
  src\
    Cdn\
      Cdn.Autorest\        ← AutoRest project root (work here)
      README.md          ← AutoRest config: input swagger, directives, version
      exports/           ← Generated public cmdlets (.ps1)
      generated/         ← Generated internal C# code (do not edit)
      custom/            ← Hand-written cmdlet overrides and helpers (.ps1, .cs)
      examples/          ← Example .md files for each cmdlet (one per cmdlet)
      test/              ← Pester test files (.Tests.ps1) + recordings (.json)
      docs/              ← Generated help docs (rebuilt by build-module.ps1)
      build-module.ps1   ← Build script
      test-module.ps1    ← Test runner script
```

Some older modules use `generated/<Module>/<Module>.Autorest/` instead of `src/`.

---

## Key Commands

| Action | Command (run from `.Autorest/` dir) |
|--------|-------------------------------------|
| Generate code from swagger | `autorest` |
| Build module + regenerate docs | `pwsh -File ./build-module.ps1` |
| Run tests with live recording | `pwsh -File ./test-module.ps1 -Record` |
| Run tests from saved recordings | `pwsh -File ./test-module.ps1 -Playback` |

---

## Module Scope

The `Cdn` module covers two resource namespaces generated from the CDN swagger:

- **Azure CDN** — classic CDN profiles, endpoints, origins, origin groups, custom domains, policies
- **Azure Front Door Standard/Premium (CDN)** — `AzFrontDoorCdn*` cmdlets for profiles, endpoints, origins, origin groups, routes, rules, rule sets, secrets, security policies, custom domains

All cmdlets are AutoRest-generated from `specification/cdn/resource-manager/Microsoft.Cdn/Cdn/` in `azure-rest-api-specs`.
