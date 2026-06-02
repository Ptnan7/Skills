---
name: azure-edge-swagger-status
description: "Query the current swagger/API versions consumed by Azure CLI and Azure PowerShell for CDN, AFD, and Front Door, then check the local azure-rest-api-specs repo for newer stable swagger versions. Use when asked to check CLI swagger version, PowerShell swagger version, pwsh swagger version, CDN/AFD/FrontDoor API version status, or whether swagger has a stable update. Do NOT use for actually upgrading, regenerating, or editing generated code."
argument-hint: "Optionally specify service or product, e.g. 'cdn cli and pwsh stable update' or 'frontdoor current swagger version'"
---

# Azure Edge Swagger Status

## Purpose

Use this skill to answer read-only status questions for CDN, AFD, and Front Door swagger/API versions across:

- Azure CLI extensions in `extension/src/cdn` and `extension/src/front-door`
- Azure PowerShell modules in `pwsh/src/Cdn` and `pwsh/src/FrontDoor`
- Local swagger specs in `swagger/specification/cdn` and `swagger/specification/frontdoor`

This skill only reports status. If the user wants to upgrade or regenerate, hand off to `azure-cli-skill` or `azure-pwsh-skill` after presenting the status.

## Preferred Command

From the `Toolings` workspace root, run:

```powershell
.\.github\skills\azure-edge-swagger-status\scripts\check_edge_swagger_versions.ps1
```

Useful options:

```powershell
.\.github\skills\azure-edge-swagger-status\scripts\check_edge_swagger_versions.ps1 -Service Cdn
.\.github\skills\azure-edge-swagger-status\scripts\check_edge_swagger_versions.ps1 -Service FrontDoor
.\.github\skills\azure-edge-swagger-status\scripts\check_edge_swagger_versions.ps1 -Product CLI
.\.github\skills\azure-edge-swagger-status\scripts\check_edge_swagger_versions.ps1 -Product PowerShell
.\.github\skills\azure-edge-swagger-status\scripts\check_edge_swagger_versions.ps1 -FetchSwagger
.\.github\skills\azure-edge-swagger-status\scripts\check_edge_swagger_versions.ps1 -AsJson
```

Use `-FetchSwagger` only when the user asks for the latest remote status or when local swagger freshness matters. The script fetches the `swagger` repo only; it does not checkout, edit, stage, or commit files.

## What To Report

Report a compact summary for each requested target:

- Product and service, for example `CLI CDN/AFD` or `PowerShell Az.Cdn`
- Current swagger/API version source
- Current versions in use
- Latest current stable version in use, if any
- Latest stable version available in `swagger`
- Newer stable versions, if any
- Pinned swagger commit for PowerShell AutoRest README files

For CLI generated AAZ code, do not assume there is exactly one current version. A command tree can use multiple API versions at the same time. List all unique versions and compare stable updates against the highest stable version currently used.

For PowerShell, read the current version from `.Autorest/README.md` `input-file` entries and read the pinned swagger commit from `commit:`.

## Manual Fallback

If the helper script cannot run, use these sources directly:

| Target | Current version source | Latest stable source |
|--------|------------------------|----------------------|
| CLI CDN/AFD | `extension/src/cdn/azext_cdn/aaz/latest/**/*.py`, quoted API version metadata | `swagger/specification/cdn/resource-manager/Microsoft.Cdn/Cdn/stable/*` |
| CLI Front Door classic | `extension/src/front-door/azext_front_door/aaz/latest/**/*.py`, quoted API version metadata | `swagger/specification/frontdoor/resource-manager/Microsoft.Network/FrontDoor/stable/*` |
| PowerShell Az.Cdn | `pwsh/src/Cdn/Cdn.Autorest/README.md` `input-file` and `commit` | `swagger/specification/cdn/resource-manager/Microsoft.Cdn/Cdn/stable/*` |
| PowerShell Az.FrontDoor | `pwsh/src/FrontDoor/FrontDoor.Autorest/README.md` `input-file` and `commit` | `swagger/specification/frontdoor/resource-manager/Microsoft.Network/FrontDoor/stable/*` |

Suggested manual PowerShell snippets:

```powershell
rg -o '"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:-preview)?"' --no-filename extension\src\cdn\azext_cdn\aaz\latest | ForEach-Object { $_.Trim('"') } | Sort-Object -Unique
rg -o '"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:-preview)?"' --no-filename extension\src\front-door\azext_front_door\aaz\latest | ForEach-Object { $_.Trim('"') } | Sort-Object -Unique
Select-String -Path pwsh\src\Cdn\Cdn.Autorest\README.md -Pattern 'input-file:|commit:|stable/|preview/' -Context 0,3
Select-String -Path pwsh\src\FrontDoor\FrontDoor.Autorest\README.md -Pattern 'input-file:|commit:|stable/|preview/' -Context 0,3
Get-ChildItem swagger\specification\cdn\resource-manager\Microsoft.Cdn\Cdn\stable -Directory | Select-Object -ExpandProperty Name
Get-ChildItem swagger\specification\frontdoor\resource-manager\Microsoft.Network\FrontDoor\stable -Directory | Select-Object -ExpandProperty Name
```

## Interpretation Rules

- Treat versions ending in `-preview` as preview, not stable.
- Sort API versions lexically; the `yyyy-MM-dd` format makes lexical and chronological ordering equivalent for these names.
- `HasNewerStable` is true when the latest stable swagger directory is newer than the newest current API version date consumed by that target, ignoring a `-preview` suffix for comparison.
- If a target currently uses only preview versions, keep `LatestCurrentStable` empty but still compare stable updates against the preview version date.
- Do not recommend an upgrade just because a newer stable exists. First report the status, then ask whether the user wants to inspect swagger diff or start an upgrade workflow.