---
name: azure-edge-sync-cli-pwsh-generation
description: "Coordinate Azure edge swagger/API generation across Azure CLI extensions and Azure PowerShell for CDN, AFD, and Front Door. Use when the user asks to sync CLI and PowerShell generation, compare generated changes between the extension/aaz and pwsh repos, or validate that a newly generated API surface is consistently exposed in both tools. This workflow invokes the CLI and PowerShell skills as needed, then compares their diffs and public command surfaces. Do NOT use for a CLI-only or PowerShell-only change unless the user explicitly wants cross-tool comparison."
argument-hint: "Describe the API/version/surface to sync across CLI and PowerShell"
---

# Azure Edge CLI/Pwsh Synchronized Generation

## Purpose

Use this workflow when Azure edge swagger changes should be consumed by both Azure CLI extensions and Azure PowerShell, especially for CDN, AFD, and Front Door APIs. The goal is not just to regenerate both repos, but to compare the outputs and use each repo's generated diff to validate the other.

## Required Inputs

Before editing or generating, identify:

- Product area: CDN, AFD Standard/Premium, or Front Door classic.
- Swagger API version and swagger repo branch/commit.
- Target surfaces: specific commands/cmdlets, resources, properties, examples, or tests.
- Repos involved: usually `extension`, `aaz`, `pwsh`, and `swagger`.

## Workflow

1. Load and follow `azure-cli-skill` for CLI/AAZ generation steps.
2. Load and follow `azure-pwsh-skill` for PowerShell AutoRest generation steps.
3. Generate both sides from the same swagger version or explicitly record why versions differ.
4. If generating a new API/module version, update the corresponding docs/help/examples for each generated side and run the relevant build/generation command before comparing results.
5. After generation completes, collect `git status --short` and focused diffs from both repos:
   - `extension` and `aaz` for CLI.
   - `pwsh` for PowerShell.
6. Compare generated changes across repos before declaring either side complete.

## Cross-Repo Comparison Checklist

After both generation flows finish, compare:

- API version: CLI generated resources and PowerShell README/input-file point to the intended swagger version.
- New or changed operations: command/cmdlet surfaces exist on both sides when both products should expose them.
- New or changed properties: generated schemas, model types, object helpers, parameters, and help mention the same property shape where applicable.
- Custom code: CLI custom wrappers and PowerShell custom wrappers preserve or intentionally hide the same user-facing surface.
- Examples/help: generated examples and help do not contradict each other, especially for create vs update semantics.
- Tests/recordings: CLI scenario tests and PowerShell Pester recordings cover comparable workflows when live test coverage is expected.
- Changelog/version metadata: both repos include the expected user-facing note when the change is shipped in both tools.

## Validation Rules

- If one repo exposes a generated property and the other does not, inspect whether a custom wrapper, exported command list, or object-helper generation list is hiding it.
- If PowerShell generated/internal code includes a parameter but public docs or `Get-Command` do not, check `custom/*.ps1`, generated exports, and `FunctionsToExport`.
- If CLI AAZ code includes a schema field but `az ... -h` does not show it directly, check whether the field is nested inside a complex argument such as `--managed-rules`.
- Do not treat generated files as noise simply because they were produced by AutoRest, AAZ export, or build scripts. Review them as generation output and revert only with a concrete reason.

## PowerShell-Specific Reminders

- Do not manually edit `custom/autogen-model-cmdlets`; change generation inputs such as `build-module.ps1` model cmdlet configuration, then run the build/generation flow.
- Object-helper cmdlets and model object types do not need new tests by default. Add tests only when the helper has custom behavior beyond simple property assignment or the user explicitly asks.
- For a new generated version, update generated docs/help/examples and run `build-module.ps1` so public docs, exports, manifests, and helpers match the generated API surface.
- PowerShell recordings must come from `test-module.ps1 -Record`; do not synthesize or patch recording JSON.

## CLI-Specific Reminders

- Export AAZ before generating CLI when using AAZ workspace changes.
- Do not hand-edit generated AAZ repo files after export; adjust the workspace/source generation inputs instead.
- Run `azdev linter <ext>` when appropriate, but route scenario test creation/execution through the test workflow when the user asks for tests.

## Reporting

When summarizing, include:

- Branches and commits for each repo touched.
- The swagger version/commit used by each side.
- A short cross-tool comparison table: CLI exposed, PowerShell exposed, discrepancy, resolution.
- Validation commands run and their pass/fail counts.
