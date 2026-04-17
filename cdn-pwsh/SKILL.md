---
name: cdn-pwsh
description: "Maintain CDN/AFD AutoRest-generated Azure PowerShell modules. Use when updating a .Autorest README.md, regenerating a PowerShell module from swagger, fixing autorest or build-module.ps1 failures, identifying new or removed cmdlets, adding example docs or Pester tests, or merging separate CRUD test files into a single New-* test flow. Do NOT use for Azure CLI work, non-AutoRest PowerShell changes, or unrelated repository-wide refactors."
argument-hint: "Describe the PowerShell task, e.g. 'update Cdn README.md and regenerate' or 'merge CRUD tests for FrontDoor routes'"
---

# CDN PowerShell Module Maintenance

## Overview

This skill covers maintaining the CDN/AFD AutoRest-generated Azure PowerShell module (under `src/Cdn/` in the `azure-powershell` repo). Load the reference file that matches the task.

## Environment Setup

One-time initialization (clones `azure-powershell` as `pwsh` and `azure-rest-api-specs` as `swagger` into the workspace):

```powershell
& .github\cdn-pwsh\scripts\initialize_pwsh_env.ps1
```

For every new terminal:

```powershell
. .github\cdn-pwsh\scripts\use_pwsh_env.ps1
```

This sets `$env:PWSH_REPO_PATH` and `$env:AAZ_SWAGGER_PATH` for scripts and commands below.

## Quick Reference — Swagger Upgrade

1. **Initialize environment** — run `initialize_pwsh_env.ps1` (Copilot)
2. **Activate environment** — run `use_pwsh_env.ps1` in every new terminal
3. **Diff swagger** — run `python .github\cdn-cli\scripts\swagger_diff.py --ext cdn --old <old-ver> --new <new-ver>` (shared with cdn-cli)
4. **Update README.md** — update commit hash / API version / directives in `.Autorest/README.md` (see [autorest-generation.md](references/autorest-generation.md))
5. **Run autorest** — `autorest` from the `.Autorest/` directory
6. **Review custom code** — check if `custom/` files reference changed models, renamed properties, or removed types from the swagger diff. Present findings to the user and wait for approval before editing. See [autorest-generation.md](references/autorest-generation.md) Step 3.
7. **Build module** — `pwsh -File ./build-module.ps1`
8. **Identify changes** — check new/removed cmdlets (see [development.md](references/development.md))
9. **Test** — ask the user whether to run tests. If yes, run `pwsh -File ./test-module.ps1 -Playback` (see [testing.md](references/testing.md))
10. **Commit** — if tests pass (or were skipped), ask the user whether to commit. If yes, stage and commit changes in the `pwsh` repo.

## Reference Files

| File | Contents |
|------|----------|
| [architecture.md](references/architecture.md) | Module location, directory structure, key commands |
| [swagger-diff.md](references/swagger-diff.md) | Compare old vs new swagger (local or GitHub) before updating |
| [autorest-generation.md](references/autorest-generation.md) | Update README.md config, run autorest, build module, error-fixing rules |
| [development.md](references/development.md) | Identify new/removed cmdlets, update example documentation |
| [testing.md](references/testing.md) | Add Pester tests, run tests, merge CRUD tests into New-* files |
