---
name: azure-edge-swagger-diff
description: "Compare Azure edge swagger/API versions for CDN, AFD, or Front Door before CLI or PowerShell generation. Use when asked to diff swagger, prepare a swagger upgrade, identify updated/new APIs, produce AddSwagger resource candidates, or save a reusable swagger diff artifact for later generate/test workflows. Do NOT use for actually generating CLI/PowerShell code or editing tests."
argument-hint: "Describe the product and versions, e.g. 'diff cdn 2024-02-01 to 2025-09-01-preview'"
---

# Azure Edge Swagger Diff

## Purpose

Use this skill as the first step for Azure edge swagger upgrades shared by CLI, PowerShell, and cross-tool generation workflows. It produces a persisted diff artifact that later generation and test skills can reuse instead of redoing or re-summarizing the same comparison.

## Inputs To Identify

- Product area: `cdn` for CDN/AFD Standard/Premium, or `front-door` for Front Door classic.
- Old API version and new API version.
- Swagger source: local `swagger` repo path, current branch, and commit when relevant.
- The downstream workflow that will consume the diff: CLI generation, PowerShell generation, synchronized generation, or test planning.

## Environment

Activate either environment before running the shared diff script:

```powershell
. .github\skills\azure-cli-skill\scripts\use_aaz_dev_env.ps1
```

or:

```powershell
. .github\skills\azure-pwsh-skill\scripts\use_pwsh_env.ps1
```

Both set `AAZ_SWAGGER_PATH` for the local `azure-rest-api-specs` clone.

## Run The Diff

Run from the Toolings workspace root so the default output folder is created at `swagger-diffs/`:

```powershell
python .github\skills\azure-cli-skill\scripts\swagger_diff.py --ext <cdn|front-door> --old <old-version> --new <new-version>
```

Use `--swagger-path <path>` when the swagger repo is not the one pointed to by the active environment.

The script prints the diff and also saves it by default to:

```text
swagger-diffs/<ext>/<old-version>_to_<new-version>.md
```

Use `--output-dir <dir>` to choose a different root folder, or `--no-save` only when a persisted artifact is explicitly unnecessary.

## Required Summary

After running the diff, report these items to the user and reference the saved diff file:

- Saved diff path.
- Updated APIs: existing method/path operations whose parameters changed.
- New APIs: method/path operations absent from the old swagger.
- Removed APIs and breaking changes.
- AddSwagger resource candidates printed by the script.
- Any swagger branch/commit assumptions that affect the result.

Wait for the user to acknowledge the swagger diff before starting CLI generation, PowerShell generation, AddSwagger workspace edits, or test updates.

## Artifact Contract

Downstream skills should treat the saved markdown file as the handoff artifact:

- CLI generation uses it to choose AddSwagger candidates and custom-code review focus.
- PowerShell generation uses it to choose README directives, custom wrapper review focus, and cmdlet impact checks.
- Test workflows use it to identify new/changed operations that may need scenario or Pester coverage.

Do not overwrite the user's interpretation of a previously acknowledged diff without saying that the swagger branch, version, or source path changed.