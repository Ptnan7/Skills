[CmdletBinding()]
param(
    [ValidateSet('All', 'Cdn', 'FrontDoor')]
    [string] $Service = 'All',

    [ValidateSet('All', 'CLI', 'PowerShell')]
    [string] $Product = 'All',

    [switch] $FetchSwagger,

    [switch] $AsJson
)

$ErrorActionPreference = 'Stop'

function Get-WorkspaceRoot {
    $scriptDirectory = Split-Path -Parent $PSCommandPath
    return (Resolve-Path (Join-Path $scriptDirectory '..\..\..\..')).Path
}

function Join-WorkspacePath {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Root,

        [Parameter(Mandatory = $true)]
        [string] $RelativePath
    )

    return Join-Path $Root $RelativePath
}

function Get-VersionSortValue {
    param([string] $Version)
    return $Version -replace '-preview$', ''
}

function Sort-ApiVersions {
    param([string[]] $Versions)

    return @($Versions | Where-Object { $_ } | Sort-Object @{ Expression = { Get-VersionSortValue $_ } }, @{ Expression = { $_ -like '*-preview' } } -Unique)
}

function Get-StableSwaggerVersions {
    param([string] $StableDirectory)

    if (-not (Test-Path $StableDirectory)) {
        return @()
    }

    return @(Get-ChildItem $StableDirectory -Directory |
        Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}$' } |
        Select-Object -ExpandProperty Name |
        Sort-Object -Unique)
}

function Get-CliVersions {
    param([string] $SourceDirectory)

    if (-not (Test-Path $SourceDirectory)) {
        return @()
    }

    $matches = Get-ChildItem $SourceDirectory -Recurse -File -Include '*.py' |
        Select-String -Pattern '"(?<version>\d{4}-\d{2}-\d{2}(?:-preview)?)"' -AllMatches |
        ForEach-Object { $_.Matches } |
        ForEach-Object { $_.Groups['version'].Value }

    return @(Sort-ApiVersions $matches)
}

function Get-PowerShellReadmeInfo {
    param([string] $ReadmePath)

    if (-not (Test-Path $ReadmePath)) {
        return [PSCustomObject]@{
            Versions = @()
            Commit = $null
        }
    }

    $content = Get-Content $ReadmePath -Raw
    $versionMatches = [regex]::Matches($content, 'specification[\\/].*?[\\/](?:stable|preview)[\\/](?<version>\d{4}-\d{2}-\d{2}(?:-preview)?)[\\/]openapi\.json')
    $versions = @($versionMatches | ForEach-Object { $_.Groups['version'].Value })
    $commitMatch = [regex]::Match($content, '(?m)^\s*commit:\s*(?<commit>\S+)\s*$')
    $commit = if ($commitMatch.Success) { $commitMatch.Groups['commit'].Value } else { $null }

    return [PSCustomObject]@{
        Versions = @(Sort-ApiVersions $versions)
        Commit = $commit
    }
}

function New-StatusResult {
    param(
        [hashtable] $Target,
        [string] $WorkspaceRoot
    )

    $stableDirectory = Join-WorkspacePath -Root $WorkspaceRoot -RelativePath $Target.StableDirectory
    $stableVersions = @(Get-StableSwaggerVersions -StableDirectory $stableDirectory)
    $latestStable = @($stableVersions | Sort-Object | Select-Object -Last 1)[0]
    $commit = $null

    if ($Target.Product -eq 'CLI') {
        $sourcePath = Join-WorkspacePath -Root $WorkspaceRoot -RelativePath $Target.SourcePath
        $currentVersions = @(Get-CliVersions -SourceDirectory $sourcePath)
    }
    else {
        $sourcePath = Join-WorkspacePath -Root $WorkspaceRoot -RelativePath $Target.SourcePath
        $readmeInfo = Get-PowerShellReadmeInfo -ReadmePath $sourcePath
        $currentVersions = @($readmeInfo.Versions)
        $commit = $readmeInfo.Commit
    }

    $currentStableVersions = @($currentVersions | Where-Object { $_ -notlike '*-preview' } | Sort-Object -Unique)
    $latestCurrentStable = @($currentStableVersions | Select-Object -Last 1)[0]
    $latestCurrentVersionDate = @($currentVersions | ForEach-Object { Get-VersionSortValue $_ } | Sort-Object -Unique | Select-Object -Last 1)[0]
    $newerStableVersions = if ($latestCurrentVersionDate) {
        @($stableVersions | Where-Object { $_ -gt $latestCurrentVersionDate })
    }
    else {
        @($stableVersions)
    }

    return [PSCustomObject]@{
        Target = $Target.Name
        Product = $Target.Product
        Service = $Target.Service
        CurrentSource = $Target.SourcePath
        CurrentVersions = @($currentVersions)
        LatestCurrentStable = $latestCurrentStable
        LatestCurrentVersionDate = $latestCurrentVersionDate
        LatestSwaggerStable = $latestStable
        HasNewerStable = [bool]($newerStableVersions.Count -gt 0)
        NewerStableVersions = @($newerStableVersions)
        PinnedSwaggerCommit = $commit
        StableSource = $Target.StableDirectory
    }
}

$workspaceRoot = Get-WorkspaceRoot
$swaggerRoot = Join-WorkspacePath -Root $workspaceRoot -RelativePath 'swagger'

if ($FetchSwagger -and (Test-Path (Join-Path $swaggerRoot '.git'))) {
    git -C $swaggerRoot fetch --prune | Out-Null
}

$targets = @(
    @{
        Name = 'CLI CDN/AFD'
        Product = 'CLI'
        Service = 'Cdn'
        SourcePath = 'extension/src/cdn/azext_cdn/aaz/latest'
        StableDirectory = 'swagger/specification/cdn/resource-manager/Microsoft.Cdn/Cdn/stable'
    },
    @{
        Name = 'CLI Front Door classic'
        Product = 'CLI'
        Service = 'FrontDoor'
        SourcePath = 'extension/src/front-door/azext_front_door/aaz/latest'
        StableDirectory = 'swagger/specification/frontdoor/resource-manager/Microsoft.Network/FrontDoor/stable'
    },
    @{
        Name = 'PowerShell Az.Cdn'
        Product = 'PowerShell'
        Service = 'Cdn'
        SourcePath = 'pwsh/src/Cdn/Cdn.Autorest/README.md'
        StableDirectory = 'swagger/specification/cdn/resource-manager/Microsoft.Cdn/Cdn/stable'
    },
    @{
        Name = 'PowerShell Az.FrontDoor'
        Product = 'PowerShell'
        Service = 'FrontDoor'
        SourcePath = 'pwsh/src/FrontDoor/FrontDoor.Autorest/README.md'
        StableDirectory = 'swagger/specification/frontdoor/resource-manager/Microsoft.Network/FrontDoor/stable'
    }
)

$filteredTargets = $targets | Where-Object {
    ($Service -eq 'All' -or $_.Service -eq $Service) -and
    ($Product -eq 'All' -or $_.Product -eq $Product)
}

$results = @($filteredTargets | ForEach-Object { New-StatusResult -Target $_ -WorkspaceRoot $workspaceRoot })

if ($AsJson) {
    $results | ConvertTo-Json -Depth 5
    return
}

$results |
    Select-Object `
        Target, `
        @{ Name = 'CurrentVersions'; Expression = { ($_.CurrentVersions -join ', ') } }, `
        LatestCurrentStable, `
        LatestCurrentVersionDate, `
        LatestSwaggerStable, `
        HasNewerStable, `
        @{ Name = 'NewerStableVersions'; Expression = { ($_.NewerStableVersions -join ', ') } }, `
        PinnedSwaggerCommit, `
        CurrentSource |
    Format-Table -AutoSize