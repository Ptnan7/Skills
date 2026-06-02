# Presentation Notes: Copilot Skills for Azure Edge Tooling

Date: 2026-06-02

## Executive Summary

Today we improved the local Copilot skill system for Azure CDN, Azure Front Door, Azure CLI, and Azure PowerShell maintenance. The work focused on making routine engineering workflows more discoverable, repeatable, and safer for future automation.

The main additions were:

- A new status-check skill for identifying the current CLI/PowerShell swagger versions and whether newer stable swagger versions exist.
- A new property-subcommand skill for handling AAZ commands generated from nested resource properties, such as `afd profile log-scrubbing show`.
- Helper-script improvements so CDN CLI generation can preserve known old-API pins instead of blindly forcing every command to the target API.
- A successful CDN/AFD CLI refresh to Microsoft.Cdn stable API `2025-12-01`, with validation results recorded.

## New Skill: `azure-edge-swagger-status`

Path:

```text
.github/skills/azure-edge-swagger-status/SKILL.md
```

Purpose:

- Query current swagger/API versions consumed by Azure CLI and Azure PowerShell.
- Check the local `azure-rest-api-specs` repo for newer stable swagger versions.
- Report status without editing or regenerating code.

Helper script:

```text
.github/skills/azure-edge-swagger-status/scripts/check_edge_swagger_versions.ps1
```

Example command:

```powershell
.\.github\skills\azure-edge-swagger-status\scripts\check_edge_swagger_versions.ps1 -Product CLI -FetchSwagger -AsJson
```

Result found today:

- CLI CDN/AFD had a newer stable version available: `2025-12-01`.
- CLI Front Door classic was already current at `2025-11-01`.
- PowerShell Az.Cdn was using `2025-09-01-preview` and also had `2025-12-01` available as newer stable.
- PowerShell Az.FrontDoor was already current at `2025-11-01`.

Presentation angle:

- This skill turns a manual repo inspection task into a reliable status report.
- It separates read-only discovery from upgrade/regeneration workflows.

## New Skill: `azure-cli-aaz-property-subcommands`

Path:

```text
.github/skills/azure-cli-aaz-property-subcommands/SKILL.md
```

Purpose:

- Handle AAZ commands generated from nested resource properties rather than standalone swagger operations.
- Document how to refresh commands like `afd profile log-scrubbing show/create/update/delete` when the parent resource supports a newer API version.
- Prevent permanent old-version pins when the target resource model actually contains the nested property.

Key example:

```text
afd profile log-scrubbing show
```

Why this mattered:

- This command is derived from `properties.logScrubbing` on the profile resource.
- The target `2025-12-01` resource cfg contains `properties.logScrubbing`.
- The command markdown initially lacked a real `2025-12-01` property-subcommand model, so CLI generation had to pin it to `2025-06-01`.

Correct future workflow:

1. Verify the target resource cfg and swagger contain the nested property.
2. Use the AAZ Web UI to refresh or recreate the property subcommand model at the target API version.
3. Export AAZ.
4. Remove the stale pin only after the target-version markdown/model exists.
5. Regenerate CLI and validate that the generated Python uses the target API.

Presentation angle:

- Not every generated command maps to a standalone swagger operation.
- Property subcommands need a different mental model and a different repair workflow.
- The new skill prevents future agents from misclassifying these commands as permanently unsupported.

## Updated Skill Helpers

Files changed:

```text
.github/skills/azure-cli-skill/scripts/generate_cli.py
.github/skills/azure-cli-skill/scripts/auto_select_resources.py
```

Change summary:

- Added `PINNED_COMMAND_VERSIONS` support for known commands that do not have target AAZ command models.
- Updated version bump logic so it can preserve specific old API versions during CLI generation.
- Printed pinned command details during dry-run and generation.

Known pins added for CDN `2025-12-01`:

```text
afd profile log-scrubbing show -> 2025-06-01
cdn profile deployment-version approve -> 2025-09-01-preview
cdn profile deployment-version compare -> 2025-09-01-preview
cdn profile deployment-version list -> 2025-09-01-preview
cdn profile deployment-version show -> 2025-09-01-preview
cdn profile deployment-version update -> 2025-09-01-preview
```

Why this was needed:

- AAZ CLI generation failed when every command was forced to `2025-12-01`.
- Some commands have no target command model in AAZ even though the overall module is being upgraded.
- The safer behavior is to upgrade everything possible while explicitly pinning the small known exception list.

Presentation angle:

- This is a practical guardrail against over-aggressive automation.
- The helper makes the exception list explicit and reviewable.

## CLI Refresh Completed: CDN/AFD `2025-12-01`

Repos/branches:

```text
extension: update-cdn-2025-12-01
aaz:       update-cdn-2025-12-01
```

Workflow completed:

1. Checked working trees for `extension`, `aaz`, and `swagger`.
2. Initialized and activated the AAZ dev environment.
3. Ran swagger diff:
   - `2025-06-01` -> `2025-12-01`
   - `2025-09-01-preview` -> `2025-12-01`
4. Created AAZ workspace `cdn-2025-12-01`.
5. Added all selected existing CDN/AFD resources.
6. Confirmed there were no new API paths in the stable diff.
7. Exported AAZ.
8. Generated CLI extension code.
9. Fixed a generated/custom argument conflict in `custom_afdx.py`.
10. Updated package version and history.
11. Validated the result.

Important swagger diff summary:

- Updated API: `RuleSets_Create` PUT on `/profiles/{profileName}/ruleSets/{ruleSetName}`.
- New stable API paths: none.
- New/changed model surface included batch rule-set update changes.

Extension updates:

```text
extension/src/cdn/setup.py: 1.0.0b1 -> 1.0.0b2
extension/src/cdn/HISTORY.rst: added 1.0.0b2 entry
extension/src/cdn/azext_cdn/custom/custom_afdx.py: guarded health probe custom args
```

Validation completed:

- Generated Python AST syntax check passed for `178` files.
- Static CDN linter passed:
  ```powershell
  azdev linter cdn -t help_entries command_groups commands params
  ```
- API version scan found only the expected six pinned commands.
- Update-example scan found no stale generated `Create(s)` wording in update examples.

Note about linter environment:

- The full default `azdev linter cdn` first exposed environment dependency gaps.
- After dependencies were addressed, all static rules passed.
- The recommended clean command for this workflow is the static rule set shown above.

## Key Lessons Learned

- Swagger version status should be checked before starting an upgrade; it avoids unnecessary regeneration.
- CDN/AFD CLI generation cannot blindly bump every command to the target API version.
- Property subcommands need explicit AAZ Web UI refresh when their target-version command model is missing.
- Test generation remains separate and should be handled by `azure-cli-test-skill` with user approval before running tests.
- Skills work best when they encode both the happy path and the recurring edge cases.

## Suggested Presentation Structure

1. Problem: Azure edge CLI/Pwsh maintenance has repeated manual discovery and generation steps.
2. Solution: Codify workflows as Copilot skills with clear trigger descriptions.
3. Demo 1: Use `azure-edge-swagger-status` to detect newer stable swagger versions.
4. Demo 2: Show CDN/AFD `2025-12-01` generation and pinned-command handling.
5. Demo 3: Explain `afd profile log-scrubbing` as a property subcommand and why it needs a dedicated skill.
6. Wrap-up: Skills reduce context loss, make edge cases repeatable, and make future automation safer.

## Open Follow-Ups

- Use `azure-cli-aaz-property-subcommands` to refresh `afd profile log-scrubbing show` to `2025-12-01` through the AAZ Web UI.
- Decide whether to expose `afd profile log-scrubbing create/update/delete` in the CLI command table, since AAZ has those command markdown files but the extension currently registers only `show`.
- Hand off to `azure-cli-test-skill` for test impact analysis and scenario updates before running scenario tests.
- Commit/push the skill helper updates and the new property-subcommand skill after review.