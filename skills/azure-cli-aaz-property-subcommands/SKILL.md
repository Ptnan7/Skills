---
name: azure-cli-aaz-property-subcommands
description: "Upgrade or repair Azure CLI AAZ property subcommands generated from nested resource properties, such as afd profile log-scrubbing show/create/update/delete. Use when a CDN/AFD command is pinned to an old API because it is a property subcommand, when the target swagger resource contains the property but the AAZ command markdown lacks the target version, or when Web UI-generated subcommands need to be refreshed for a new stable API. Do NOT use for ordinary swagger operation commands or scenario tests."
argument-hint: "Describe the property subcommand and target API, e.g. 'upgrade afd profile log-scrubbing show to 2025-12-01'"
---

# Azure CLI AAZ Property Subcommands

## Purpose

Use this skill for AAZ commands that are not standalone swagger operations. These commands are carved out of a parent resource property by the AAZ Web UI, for example:

- `afd profile log-scrubbing show`
- `afd profile log-scrubbing create`
- `afd profile log-scrubbing update`
- `afd profile log-scrubbing delete`

These commands usually point to a parent resource path plus a property selector, such as:

```text
/subscriptions/{}/resourcegroups/{}/providers/microsoft.cdn/profiles/{} 2025-06-01 properties.logScrubbing
```

Do not treat them as missing swagger operations. First check whether the target API resource model contains the property and whether the AAZ command model was generated for that target version.

## When To Use

Use this skill when any of these signals appear:

- `generate_cli.py` or `auto_select_resources.py` pins a command because the target version is missing.
- A command markdown under `aaz/Commands/...` has old versions but lacks the target version.
- The target resource cfg under `aaz/Resources/.../<target-version>.xml` contains the nested property and args/props.
- The extension has generated parent commands with the nested property, but a separate child command still points at an old API.

Do not use this skill when the command maps to a normal swagger operation path. Use `azure-cli-skill` for ordinary operation/resource generation.

## Current Example: AFD Profile Log Scrubbing

During the CDN `2025-12-01` stable refresh, `afd profile log-scrubbing show` looked like a missing target command model, but the target resource did contain the property:

- Existing command markdown: `aaz/Commands/afd/profile/log-scrubbing/_show.md`
- Existing extension command: `extension/src/cdn/azext_cdn/aaz/latest/afd/profile/log_scrubbing/_show.py`
- Extension registration: `extension/src/cdn/azext_cdn/commands.py`
- Custom wrapper: `extension/src/cdn/azext_cdn/custom/custom_afdx.py`
- Target resource cfg: `aaz/Resources/mgmt-plane/...profiles/{}/2025-12-01.xml`
- Property: `properties.logScrubbing`

In that state, the correct next step is not to keep the pin forever. Instead, refresh or recreate the property subcommand in AAZ so its markdown/model has the target API version, then remove the old pin and regenerate CLI.

## Required Workflow

1. **Classify the command.** Confirm whether the pinned command is a property subcommand. Look for markdown comments ending with a property path, for example `properties.logScrubbing`.
2. **Verify target property support.** Inspect the target resource cfg and swagger:
   ```powershell
   rg "logScrubbing|properties.logScrubbing" aaz\Resources\mgmt-plane\**\2025-12-01.xml
   rg "logScrubbing" swagger\specification\cdn\resource-manager\Microsoft.Cdn\Cdn\stable\2025-12-01\openapi.json
   ```
3. **Inspect existing command markdown.** Confirm whether the target version is missing:
   ```powershell
   Get-Content aaz\Commands\afd\profile\log-scrubbing\_show.md
   ```
4. **Use AAZ Web UI to refresh the property subcommand.** Open `http://127.0.0.1:5000`, load the workspace containing the parent resource at the target version, and use the Workspace Editor to create or refresh the property command under the parent command group.
5. **Export AAZ.** Export from the Web UI or helper workflow after the property command model is present.
6. **Remove stale pins.** Remove the command from `PINNED_COMMAND_VERSIONS` only after the AAZ command markdown has a real target-version entry and the linked resource cfg contains the property command model.
7. **Generate CLI.** Run the normal generation flow from `azure-cli-skill`.
8. **Validate.** Confirm the generated Python uses the target API, then run syntax checks and linter.

## Checks Before Removing A Pin

A pin can be removed only when all checks pass:

- The command markdown has `### [<target-version>]`.
- The markdown comment includes the target version and property path.
- The target resource cfg contains both the input args and output props for the property.
- `python .github\skills\azure-cli-skill\scripts\generate_cli.py --ext cdn --version <target-version> --dry-run` no longer needs to list the command as pinned.
- A real generate run succeeds without `Version '<target-version>' of command '<command>' not exist in AAZ`.

Do not add a markdown-only version entry by hand. A markdown entry without a real resource cfg model can still fail generation.

## CLI Registration Rules

If the property command already exists in the extension command table, refresh only that existing command surface. For example, `afd profile log-scrubbing show` is registered through a custom wrapper.

If create/update/delete property commands exist in AAZ but are not currently registered in the extension, do not expose them automatically during a swagger refresh. Ask the user whether they want to expand the CLI command surface. Parent commands such as `afd profile create/update --log-scrubbing ...` may already cover write scenarios.

## Validation Commands

Check for non-target API pins after generation:

```powershell
$target = "2025-12-01"
Get-ChildItem -Path extension\src\cdn\azext_cdn\aaz\latest -Recurse -Filter "*.py" |
  Select-String -Pattern '"api-version", "([0-9]{4}-[0-9]{2}-[0-9]{2}(?:-preview)?)"' |
  Where-Object { $_.Matches[0].Groups[1].Value -ne $target }
```

Check the specific property command:

```powershell
Select-String -Path extension\src\cdn\azext_cdn\aaz\latest\afd\profile\log_scrubbing\_show.py -Pattern '"api-version"|properties.logScrubbing|logScrubbing'
```

Run static linter only for a clean result:

```powershell
azdev linter cdn -t help_entries command_groups commands params
```

Scenario tests are owned by `azure-cli-test-skill`; do not run them without explicit user approval.