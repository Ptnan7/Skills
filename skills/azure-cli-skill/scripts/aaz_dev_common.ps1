Set-StrictMode -Version Latest

$script:AazDevRequiredRepos = @("extension", "swagger", "aaz", "cli")

function Get-AazDevDefaultRepoRoot {
    return (Join-Path $env:USERPROFILE "source\repos")
}

function Get-AazDevRepoMatchCount {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $count = 0
    foreach ($repoName in $script:AazDevRequiredRepos) {
        if (Test-Path (Join-Path $Path $repoName)) {
            $count += 1
        }
    }

    return $count
}

function Find-AazDevRepoRootFromPath {
    [CmdletBinding()]
    param(
        [string]$StartPath
    )

    if (-not $StartPath) {
        return $null
    }

    $candidate = [System.IO.Path]::GetFullPath($StartPath)
    while ($true) {
        if ((Get-AazDevRepoMatchCount -Path $candidate) -ge 2) {
            return $candidate
        }

        $parent = Split-Path $candidate -Parent
        if (-not $parent -or $parent -eq $candidate) {
            break
        }

        $candidate = $parent
    }

    return $null
}

function Get-AazDevRepoRoot {
    [CmdletBinding()]
    param(
        [string]$RepoRoot
    )

    if ($RepoRoot) {
        return [System.IO.Path]::GetFullPath($RepoRoot)
    }

    if ($env:AAZ_REPOS_ROOT) {
        return [System.IO.Path]::GetFullPath($env:AAZ_REPOS_ROOT)
    }

    $detectedRepoRoot = Find-AazDevRepoRootFromPath -StartPath (Get-Location).Path
    if ($detectedRepoRoot) {
        return $detectedRepoRoot
    }

    return (Get-AazDevDefaultRepoRoot)
}

function Get-AazDevContext {
    [CmdletBinding()]
    param(
        [string]$RepoRoot,
        [string]$VenvName = "azdev"
    )

    $resolvedRepoRoot = Get-AazDevRepoRoot -RepoRoot $RepoRoot

    return [pscustomobject]@{
        RepoRoot      = $resolvedRepoRoot
        VenvName      = $VenvName
        VenvPath      = (Join-Path $resolvedRepoRoot $VenvName)
        ActivatePath  = (Join-Path $resolvedRepoRoot "$VenvName\Scripts\Activate.ps1")
        SwaggerPath   = (Join-Path $resolvedRepoRoot "swagger")
        AazPath       = (Join-Path $resolvedRepoRoot "aaz")
        CliPath       = (Join-Path $resolvedRepoRoot "cli")
        ExtensionPath = (Join-Path $resolvedRepoRoot "extension")
    }
}

function Set-AazDevEnvironment {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context
    )

    $env:AAZ_REPOS_ROOT = $Context.RepoRoot
    $env:AAZ_SWAGGER_PATH = $Context.SwaggerPath
    $env:AAZ_PATH = $Context.AazPath
    $env:AAZ_CLI_PATH = $Context.CliPath
    $env:AAZ_CLI_EXTENSION_PATH = $Context.ExtensionPath
}

function Test-AazDevGitRepo {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return (Test-Path (Join-Path $Path ".git"))
}