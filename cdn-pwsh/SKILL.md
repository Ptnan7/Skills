---
name: cdn-pwsh
description: "Maintain CDN/AFD AutoRest-generated Azure PowerShell modules. Use when updating a .Autorest README.md, regenerating a PowerShell module from swagger, fixing autorest or build-module.ps1 failures, identifying new or removed cmdlets, adding example docs or Pester tests, or merging separate CRUD test files into a single New-* test flow. Do NOT use for Azure CLI work, non-AutoRest PowerShell changes, or unrelated repository-wide refactors."
argument-hint: "Describe the PowerShell task, e.g. 'update Cdn README.md and regenerate' or 'merge CRUD tests for FrontDoor routes'"
---

# CDN PowerShell Module Maintenance

## Overview

This skill covers maintaining the CDN/AFD AutoRest-generated Azure PowerShell module (under `src/Cdn/` in the `azure-powershell` repo). Load the reference file that matches the task.

## Reference Files

| File | Contents |
|------|----------|
| [architecture.md](references/architecture.md) | Module location, directory structure, key commands |
| [swagger-diff.md](references/swagger-diff.md) | Compare old vs new swagger (local or GitHub) before updating |
| [autorest-generation.md](references/autorest-generation.md) | Update README.md config, run autorest, build module, error-fixing rules |
| [development.md](references/development.md) | Identify new/removed cmdlets, update example documentation |
| [testing.md](references/testing.md) | Add Pester tests, run tests, merge CRUD tests into New-* files |
