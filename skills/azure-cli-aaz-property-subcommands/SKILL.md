---
name: azure-cli-aaz-property-subcommands
description: "Generate, upgrade, or repair Azure CLI AAZ property/subresource subcommands carved from nested resource properties, such as afd profile log-scrubbing show/create/update/delete or network front-door waf-policy managed-rules exception add/list/remove. Use when a CDN/AFD/Front Door command is pinned to an old API because it is a property subcommand, when a target swagger resource contains the property but AAZ command markdown lacks the target version, or when Web UI-generated subcommands need to be created/refreshed for a new stable API. Do NOT use for ordinary swagger operation commands or scenario tests."
argument-hint: "Describe the property/subresource command and target API, e.g. 'generate front-door waf-policy managed-rules exception add/list/remove for 2025-11-01'"
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
- A user asks to add CLI subcommands for a nested property, for example `az network front-door waf-policy managed-rules exception add/list/remove`, and the parent create/update command already exposes the full nested object as an argument.
- A command markdown under `aaz/Commands/...` has old versions but lacks the target version.
- The target resource cfg under `aaz/Resources/.../<target-version>.xml` contains the nested property and args/props.
- The extension has generated parent commands with the nested property, but a separate child command still points at an old API.
- `generate_cli.py` fails with `Version '<target-version>' of command '<command>' not exist in AAZ` and the command markdown comment includes a nested property path.

Do not use this skill when the command maps to a normal swagger operation path. Use `azure-cli-skill` for ordinary operation/resource generation.

## Known CDN/AFD Property Subcommands

Check this list before deciding that a missing target command model must be pinned:

| Command group | Parent resource | Property arg/path | Current caution |
|---------------|-----------------|-------------------|-----------------|
| `afd profile log-scrubbing` | `/subscriptions/{}/resourcegroups/{}/providers/microsoft.cdn/profiles/{}` | `properties.logScrubbing` | Some extension profiles register only `show`; avoid expanding create/update/delete surface by accident. |
| `afd rule action` | `/subscriptions/{}/resourcegroups/{}/providers/microsoft.cdn/profiles/{}/rulesets/{}/rules/{}` | `properties.actions[]` / `$rule.properties.actions` | Generate/refresh all registered verbs for the target API before pinning. |
| `afd rule condition` | `/subscriptions/{}/resourcegroups/{}/providers/microsoft.cdn/profiles/{}/rulesets/{}/rules/{}` | `properties.conditions[]` / `$rule.properties.conditions` | Generate/refresh all registered verbs for the target API before pinning. |

If a new CDN/AFD command joins this list during an upgrade, update both this section and `azure-cli-skill/issues/cdn-missing-target-command-model.md` so future runs classify it correctly.

## Current Example: AFD Profile Log Scrubbing

During the CDN `2025-12-01` stable refresh, `afd profile log-scrubbing show` looked like a missing target command model, but the target resource did contain the property:

- Existing command markdown: `aaz/Commands/afd/profile/log-scrubbing/_show.md`
- Existing extension command: `extension/src/cdn/azext_cdn/aaz/latest/afd/profile/log_scrubbing/_show.py`
- Extension registration: `extension/src/cdn/azext_cdn/commands.py`
- Custom wrapper: `extension/src/cdn/azext_cdn/custom/custom_afdx.py`
- Target resource cfg: `aaz/Resources/mgmt-plane/...profiles/{}/2025-12-01.xml`
- Property: `properties.logScrubbing`

In that state, the correct next step is not to keep the pin forever. Instead, refresh or recreate the property subcommand in AAZ so its markdown/model has the target API version, then remove the old pin and regenerate CLI.

## Current Example: Front Door WAF Managed Rule Exceptions

Classic Front Door WAF policy has `exceptionsList` under `managedRules`. A user may expect commands like:

```text
az network front-door waf-policy managed-rules exception add
az network front-door waf-policy managed-rules exception list
az network front-door waf-policy managed-rules exception remove
```

This is a property/subresource command set, not a standalone swagger operation. The parent resource is:

```text
/subscriptions/{}/resourcegroups/{}/providers/microsoft.network/frontdoorwebapplicationfirewallpolicies/{}
```

For API `2025-11-01`, the resource cfg contains:

```text
properties.managedRules.exceptionsList.exceptions[]
$parameters.properties.managedRules.exceptionsList.exceptions
```

Generate it through the AAZ Web UI/workspace APIs, then export and generate the `front-door` extension. Do not implement it in `src/front-door` legacy files such as `custom_waf.py`, `commands.py`, `_params.py`, or `_help.py`.

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

If the failure came from `generate_cli.py`, repeat the same generate command after refreshing the subcommand. Do not grow `PINNED_COMMAND_VERSIONS` until the property-subcommand path has been checked and either ruled out or intentionally deferred.

## Generate New Subresource Commands

Use this workflow when the parent command model exists and the goal is to create a new subcommand group from a nested property.

1. **Start the AAZ Web UI.**
    ```powershell
    & .github\skills\azure-cli-skill\scripts\restart_aaz_dev.ps1
    ```
2. **Create or open a workspace containing the parent resource.** Prefer the Web UI. The equivalent API flow is useful for repeatable runs:
    ```powershell
    $base = 'http://127.0.0.1:5000'
    $ws = 'front-door-waf-exceptions-2025-11-01'
    $resourceId = '/subscriptions/{}/resourcegroups/{}/providers/microsoft.network/frontdoorwebapplicationfirewallpolicies/{}'
    $version = '2025-11-01'

    Invoke-RestMethod -Method Post -Uri "$base/AAZ/Editor/Workspaces" `
       -ContentType 'application/json' `
       -Body (@{ name = $ws; plane = 'mgmt-plane'; modNames = 'frontdoor'; resourceProvider = 'Microsoft.Network'; source = 'OpenAPI' } | ConvertTo-Json)

    Invoke-RestMethod -Method Post -Uri "$base/AAZ/Editor/Workspaces/$ws/CommandTree/Nodes/aaz/AddSwagger" `
       -ContentType 'application/json' `
       -Body (@{ module = 'frontdoor'; version = $version; resources = @(@{ id = $resourceId; options = @{ aaz_version = $version } }) } | ConvertTo-Json -Depth 8)
    ```
3. **Find the nested property arg var.** Inspect the target resource XML for the parent update command. For Front Door WAF exceptions:
    ```powershell
    rg 'exceptionsList|var="[^"]*exceptions' aaz\Resources\mgmt-plane\**\2025-11-01.xml
    ```
    Use the collection arg, not a child scalar arg:
    ```text
    $parameters.properties.managedRules.exceptionsList.exceptions
    ```
4. **Create subresource commands from the arg.** This is the Web UI's subresource-generation action:
    ```powershell
    $encodedResource = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($resourceId))
    $encodedVersion = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($version))

    Invoke-RestMethod -Method Post `
       -Uri "$base/AAZ/Editor/Workspaces/$ws/Resources/$encodedResource/V/$encodedVersion/Subresources" `
       -ContentType 'application/json' `
       -Body (@{
          arg = '$parameters.properties.managedRules.exceptionsList.exceptions'
          commandGroupName = 'network front-door waf-policy managed-rules exception'
       } | ConvertTo-Json)
    ```
    If matching an existing command surface, pass `refArgsOptions` to preserve argument option names from the reference commands.
5. **Inspect generated commands before export.**
    ```powershell
    Invoke-RestMethod -Method Get `
       -Uri "$base/AAZ/Editor/Workspaces/$ws/CommandTree/Nodes/aaz/network/front-door/waf-policy/managed-rules/exception" |
       ConvertTo-Json -Depth 10
    ```
    Array subresources commonly generate `create`, `delete`, `list`, `show`, and `update` by default. If the desired CLI surface is `add/remove`, rename through the Web UI or use the API. The rename body must contain the full command path, not only the final verb:
    ```powershell
    Invoke-RestMethod -Method Post `
       -Uri "$base/AAZ/Editor/Workspaces/$ws/CommandTree/Nodes/aaz/network/front-door/waf-policy/managed-rules/exception/Leaves/create/Rename" `
       -ContentType 'application/json' `
       -Body '{"name":"network front-door waf-policy managed-rules exception add"}'

    Invoke-RestMethod -Method Post `
       -Uri "$base/AAZ/Editor/Workspaces/$ws/CommandTree/Nodes/aaz/network/front-door/waf-policy/managed-rules/exception/Leaves/delete/Rename" `
       -ContentType 'application/json' `
       -Body '{"name":"network front-door waf-policy managed-rules exception remove"}'
    ```
    **Important:** perform required renames before the first Export. If `create/delete` are exported first and then renamed to `add/remove`, the AAZ repo can be left with stale `_create.md`/`_delete.md` files or readme links. Later exports may fail with `Invalid Command Tree`, `FileNotFoundError` for `_create.md`, or a Jinja `None has no attribute 'names'` error while rendering the command group readme.

    Before exporting, verify the workspace command group has exactly the intended public leaves:
    ```powershell
    $node = Invoke-RestMethod -Method Get `
       -Uri "$base/AAZ/Editor/Workspaces/$ws/CommandTree/Nodes/aaz/network/front-door/waf-policy/managed-rules/exception"
    $node.commands.PSObject.Properties.Name | Sort-Object
    ```
    For existing CDN/AFD surfaces, expected examples include `afd rule action add/list/remove/show/update` and `afd rule condition add/list/remove/show/update`, not `create/delete`.
6. **Export the workspace.** This is equivalent to clicking **EXPORT** in the Web UI:
    ```powershell
    Invoke-RestMethod -Method Post -Uri "$base/AAZ/Editor/Workspaces/$ws/Generate"
    ```
7. **Register the new command surface in the CLI extension module.** AAZ Export creates command models in the `aaz` repo, but the extension generator only emits commands present in the extension module JSON. For brand-new subcommands, add the desired command group/commands to `/CLI/Az/Extension/Modules/<ext>` before the final `PUT`. For Front Door WAF exception `add/list/remove`:
    ```powershell
    $module = (Invoke-WebRequest -UseBasicParsing -Uri "$base/CLI/Az/Extension/Modules/front-door").Content |
       ConvertFrom-Json -AsHashtable

    $waf = $module['profiles']['latest']['commandGroups']['network']['commandGroups']['front-door']['commandGroups']['waf-policy']
    if (-not $waf.ContainsKey('commandGroups')) { $waf['commandGroups'] = @{} }
    if (-not $waf['commandGroups'].ContainsKey('managed-rules')) {
       $waf['commandGroups']['managed-rules'] = @{
          names = @('network', 'front-door', 'waf-policy', 'managed-rules')
          commandGroups = @{}
       }
    }

    $managedRules = $waf['commandGroups']['managed-rules']
    if (-not $managedRules.ContainsKey('commandGroups')) { $managedRules['commandGroups'] = @{} }
    $managedRules['commandGroups']['exception'] = @{
       names = @('network', 'front-door', 'waf-policy', 'managed-rules', 'exception')
       commands = @{}
    }

    foreach ($cmdName in @('add', 'list', 'remove')) {
       $managedRules['commandGroups']['exception']['commands'][$cmdName] = @{
          names = @('network', 'front-door', 'waf-policy', 'managed-rules', 'exception', $cmdName)
          registered = $true
          version = '2025-11-01'
       }
    }

    Invoke-RestMethod -Method Put -Uri "$base/CLI/Az/Extension/Modules/front-door" `
       -ContentType 'application/json' `
       -Body ($module | ConvertTo-Json -Depth 100)
    ```
8. **Verify AAZ, generate CLI, and lint.** If step 7 already performed the `PUT`, it has triggered code generation; `generate_cli.py` is still useful when only updating versions for already-registered commands.
    ```powershell
    . .github\skills\azure-cli-skill\scripts\use_aaz_dev_env.ps1
    aaz-dev command-model verify -a aaz -t network/front-door
    azdev linter front-door -t command_groups commands params
    ```

After generation, inspect `git status --short` in both `aaz` and `extension`, and confirm the new Python files exist under the extension AAZ tree. For the Front Door WAF exception example, expect files such as:

```text
extension/src/front-door/azext_front_door/aaz/latest/network/front_door/waf_policy/managed_rules/exception/_add.py
extension/src/front-door/azext_front_door/aaz/latest/network/front_door/waf_policy/managed_rules/exception/_list.py
extension/src/front-door/azext_front_door/aaz/latest/network/front_door/waf_policy/managed_rules/exception/_remove.py
```

Ignore unrelated dirty files and do not hand-edit generated AAZ Python to fix command shape.

For array subresource commands, check generated index and long option metadata before opening or updating an extension PR. AAZ may generate selector/index args without enough linter metadata. Fix the AAZ resource model first, then regenerate extension code. For example:

- Add `help` for generated index args such as `--exception-index` on `add` and `remove` commands.
- Add a shorter alias when all options are longer than the linter threshold, such as `--selector-operator` alongside `--selector-match-operator`.
- Add at least one example for each newly modified command that CI checks with `missing_command_example`. In AAZ command markdown, example blocks must use spaces, not tabs: four spaces before ```bash and eight spaces before command lines, or the aaz-dev parser will ignore the example.
- Re-run `azdev linter front-door -t help_entries command_groups commands params`; full local linter may still end with `invalid git repo: None` after all rules pass.

### Recovering From A Bad Subcommand Export

If a property subcommand was exported with the wrong default verbs, clean the generated AAZ command tree before retrying. Do not leave both `create/delete` and `add/remove` for the same public surface.

1. Remove stale command markdown that was generated only by the bad export, such as:
   ```text
   aaz/Commands/afd/rule/action/_create.md
   aaz/Commands/afd/rule/action/_delete.md
   aaz/Commands/afd/rule/condition/_create.md
   aaz/Commands/afd/rule/condition/_delete.md
   ```
2. Remove matching stale links from the command group `readme.md` files. AAZ-dev loads command groups from those readmes; stale links can keep pointing at deleted files and cause export failures.
3. Remove any untracked target-version resource XML/JSON created by the bad export for that subcommand if it references the wrong leaves.
4. Restart `aaz-dev` so its command tree cache reloads from the cleaned AAZ repo.
5. Create a fresh workspace or regenerate the subresource commands, apply all required renames, verify the workspace leaves, then export once.

For CDN/AFD rule action and condition, the safe order is: generate `$rule.properties.actions` / `$rule.properties.conditions`, rename `create -> add` and `delete -> remove`, verify leaves are `add/list/remove/show/update`, then Export.

## Before Push Checklist

Complete this checklist before pushing extension or AAZ PR branches. Do not rely on CI to discover these issues after the branch is already pushed.

- **Version and changelog:** update the extension `setup.py` version and `HISTORY.rst` before the first push when the generated command surface changes. For `src/front-door`, bump `src/front-door/setup.py` and add a top changelog entry in `src/front-door/HISTORY.rst`.
- **Examples:** ensure every newly modified registered command has at least one example in AAZ markdown and in generated Python docstrings. For diff-aware CI, run the closest local check, for example:
   ```powershell
   Push-Location extension
   ..\azdev\Scripts\azdev.exe linter front-door --repo ./ --src <branch-name> --tgt <merge-base-sha> --rules missing_command_example
   Pop-Location
   ```
   If local azdev reports `No commands selected to check`, still inspect the generated `_*.py` docstring and AAZ specs endpoint to confirm the example is present.
- **Linter:** run a local CI-like linter pass that includes help, command group, command, and parameter rules:
   ```powershell
   azdev linter front-door -t help_entries command_groups commands params
   ```
- **Tests:** run the focused scenario test for the new command surface after adding or updating coverage, for example:
   ```powershell
   .\azdev\Scripts\azdev.exe test test_waf_policy_managed_rules_exceptions --profile latest
   ```
- **Generated artifacts:** re-run syntax checks for touched generated/test Python files and remove validation-only `__pycache__` artifacts before committing.
- **Final diff check:** inspect `git diff --name-status <merge-base>...HEAD` before push. The Front Door command PR should contain only front-door source/test/recording/version/changelog files; AAZ PR should contain only command model/resource files.

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