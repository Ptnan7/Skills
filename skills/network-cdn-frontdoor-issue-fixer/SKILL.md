---
name: network-cdn-frontdoor-issue-fixer
description: "Issue intake and routing for Azure/azure-cli and Azure/azure-powershell open issues labeled Network - CDN or Network - Front Door. Use when asked to list, triage, reproduce, route, or attempt CDN, AFD, Front Door, Azure CLI, or Azure PowerShell fixes."
argument-hint: "Optionally specify repo, issue number, label, or limit, e.g. 'azure-powershell #12345' or 'all limit 20'"
---

# Network CDN and Front Door Issue Router

## Role

This skill is an **orchestrator**. It owns issue intake, triage, routing, status reporting, and PR hygiene for CDN/AFD/Front Door issues across:

- `Azure/azure-cli`
- `Azure/azure-powershell`

It does **not** own detailed implementation workflows. Delegate implementation to the domain skills:

| Domain | Load Skill | Typical Repos |
|--------|------------|---------------|
| Azure CLI CDN/AFD/Front Door commands, AAZ, swagger consumption, generated CLI, extension history | `azure-cli-skill` | `Toolings\extension`, `Toolings\aaz`, `Toolings\swagger` |
| Azure CLI scenario tests | `azure-cli-test-skill` | `Toolings\extension` |
| Azure PowerShell CDN/AFD/FrontDoor modules, AutoRest generation, cmdlets, examples, Pester tests | `azure-pwsh-skill` | `Toolings\pwsh`, `Toolings\swagger` |

Keep this skill small: add only cross-repo routing rules, issue-fetch tooling, known issue-specific runbooks, and PR/reporting requirements.

## Fetch Issues

Prefer the helper script:

```powershell
.\.github\skills\network-cdn-frontdoor-issue-fixer\scripts\list_network_issues.ps1
```

Useful options:

```powershell
.\.github\skills\network-cdn-frontdoor-issue-fixer\scripts\list_network_issues.ps1 -Limit 50
.\.github\skills\network-cdn-frontdoor-issue-fixer\scripts\list_network_issues.ps1 -Label "Network - CDN"
.\.github\skills\network-cdn-frontdoor-issue-fixer\scripts\list_network_issues.ps1 -Repo azure-powershell
.\.github\skills\network-cdn-frontdoor-issue-fixer\scripts\list_network_issues.ps1 -Repo All
.\.github\skills\network-cdn-frontdoor-issue-fixer\scripts\list_network_issues.ps1 -OutJson C:\Users\$env:USERNAME\AppData\Local\Temp\network-issues.json
```

If the script cannot run, use `gh issue list` directly:

```powershell
gh issue list --repo Azure/azure-cli --state open --label "Network - CDN" --limit 100 --json number,title,url,labels,assignees,createdAt,updatedAt
gh issue list --repo Azure/azure-cli --state open --label "Network - Front Door" --limit 100 --json number,title,url,labels,assignees,createdAt,updatedAt
gh issue list --repo Azure/azure-powershell --state open --label "Network - CDN" --limit 100 --json number,title,url,labels,assignees,createdAt,updatedAt
gh issue list --repo Azure/azure-powershell --state open --label "Network - Front Door" --limit 100 --json number,title,url,labels,assignees,createdAt,updatedAt
```

Do not scrape the GitHub web UI unless GitHub CLI/API access is unavailable.

## Orchestration Workflow

1. Fetch issues and present a compact grouped summary: source repo, issue number, title, labels, assignees, updated time, URL.
2. Read selected issue details with `gh issue view <number> --repo <owner/repo> --comments`.
3. Classify the issue using the routing table below.
4. Load the target domain skill before making implementation changes.
5. Let the domain skill drive code generation, command implementation, test strategy, and domain-specific validation.
6. Return here for issue-by-issue status, PR hygiene, and final reporting.

## Routing Table

| Signals | Route |
|---------|-------|
| `Azure/azure-cli` issue, `az cdn ...`, `az afd ...`, or `az network front-door ...` command/help/behavior | Load `azure-cli-skill` |
| CLI scenario tests, recordings, or test selection for `az cdn`, `az afd`, `az network front-door` | Load `azure-cli-test-skill` |
| Swagger/API shape issue that affects Azure CLI extension generation | Load `azure-cli-skill`; it may inspect `Toolings\swagger` and `Toolings\aaz` |
| `Azure/azure-powershell` issue or Az cmdlets such as `Get-AzFrontDoorCdn*`, `New-AzFrontDoorCdn*`, `Get-AzCdn*`, `New-AzCdn*` | Load `azure-pwsh-skill` |
| PowerShell examples, generated docs, AutoRest README, module regeneration, or Pester tests | Load `azure-pwsh-skill` |
| Swagger/API shape issue that affects Azure PowerShell module generation | Load `azure-pwsh-skill`; it may inspect `Toolings\swagger` |
| `az find`, CLI core search service, Aladdin/example index, or another non-owned component | Mark blocked/not-owned unless user explicitly expands scope |
| Service-side behavior, missing customer details, permissions, backend outage, or product clarification required | Mark blocked with exact follow-up needed |

## Delegation Rules

- Do not copy implementation procedures from `azure-cli-skill`, `azure-cli-test-skill`, or `azure-pwsh-skill` into this skill.
- Do not run test workflows that the target skill says require explicit user approval.
- Do not hand-edit generated AAZ or AutoRest files when the target skill requires regeneration.
- Make one issue-focused change at a time. Do not mix unrelated issue fixes.
- Never close, label, assign, or comment on GitHub issues unless the user explicitly asks.
- Never stage, commit, push, or open PRs unless the user explicitly asks.

## Known Fix Runbooks

Known runbooks are allowed here only when they help identify a recurring issue and route it to the correct domain skill.

### Front Door WAF Rule Create Missing Examples

Use this runbook for issues like Azure/azure-cli `#32736`: reference feedback says `az network front-door waf-policy rule create` still mentions `--defer`, lacks a real create example, or shows an update/match-condition example instead of a create example.

1. Confirm the target command is `az network front-door waf-policy rule create`.
2. Load `azure-cli-skill` because this is Azure CLI Front Door extension help.
3. Inspect `Toolings\extension\src\front-door\azext_front_door\custom_waf.py` to confirm `CreateCustomRule` supports initial match condition arguments:
   - `--match-variable`
   - `--operator`
   - `--values`
   - optional `--negate`
   - optional `--transforms`
4. Update only `Toolings\extension\src\front-door\azext_front_door\_help.py` unless command behavior is broken.
5. In `helps['network front-door waf-policy rule create']`:
   - Remove obsolete wording that tells users to use `--defer`.
   - Explain that create can include the initial match condition with `--match-variable`, `--operator`, and `--values`.
   - Add direct create examples, preferably one `MatchRule` and one `RateLimitRule`.
6. Validate without live Azure resources:
   - Run `python -m py_compile Toolings\extension\src\front-door\azext_front_door\_help.py`.
   - Ensure the stale phrase `Create a WAF policy custom rule. Use --defer` is gone.
   - Ensure a create example includes `--match-variable`, `--operator`, and `--values`.
7. Do not modify `az find` or CDN command code for this documentation issue.

## PR Workflow for Issue Fixes

When opening a PR for a fix produced through this router:

1. Create the PR only for the product repository that contains the actual fix. Do not include local skill files or Toolings `.github\skills` junctions in product PRs.
2. Use the fork remote as the PR branch source and the upstream product repo as the base.
3. In the PR body, include a dedicated `Related issue` section with the full original issue URL:

   ```markdown
   ## Related issue
   - https://github.com/Azure/azure-cli/issues/32736
   ```

4. Include a closing keyword when appropriate:
   - `Fixes Azure/azure-cli#32736`
   - `Fixes Azure/azure-powershell#12345`
5. If a PR was created without the full issue link, update the PR body immediately with `github-update_pull_request`.
6. Keep the PR summary scoped to the attempted issue fix and list validation that was actually run.

## Reporting Back

For each attempted issue, report:

- Source repo, issue number, title, and URL.
- Route decision and loaded domain skill.
- Status: fixed, partially fixed, not reproducible, blocked, duplicate/superseded, or not owned.
- Files changed or inspected.
- Validation performed or the reason validation was not possible.
