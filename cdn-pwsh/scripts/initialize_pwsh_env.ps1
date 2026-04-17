# Initialize local PowerShell module development dependencies.
#
# Clones the azure-powershell repo (if missing) into the workspace as "pwsh".
# Optionally clones the swagger repo (if missing) for swagger diff support.
#
# Usage:
#   & .github\cdn-pwsh\scripts\initialize_pwsh_env.ps1
#   & .github\cdn-pwsh\scripts\initialize_pwsh_env.ps1 -RepoRoot C:\myrepos
#   & .github\cdn-pwsh\scripts\initialize_pwsh_env.ps1 -SkipSwagger

param(
    [string]$RepoRoot,
    [switch]$SkipSwagger
)

$ErrorActionPreference = "Stop"

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$Arguments = @(),
        [Parameter(Mandatory = $true)]
        [string]$Description
    )

    Write-Host $Description
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

function Find-RepoRootFromPath {
    param([string]$StartPath)
    if (-not $StartPath) { return $null }
    $candidate = [System.IO.Path]::GetFullPath($StartPath)
    while ($true) {
        if (Test-Path (Join-Path $candidate "pwsh")) { return $candidate }
        $parent = Split-Path $candidate -Parent
        if (-not $parent -or $parent -eq $candidate) { break }
        $candidate = $parent
    }
    return $null
}

function Get-PwshRepoRoot {
    param([string]$RepoRoot)
    if ($RepoRoot) { return [System.IO.Path]::GetFullPath($RepoRoot) }
    if ($env:AAZ_REPOS_ROOT) { return [System.IO.Path]::GetFullPath($env:AAZ_REPOS_ROOT) }
    $detected = Find-RepoRootFromPath -StartPath (Get-Location).Path
    if ($detected) { return $detected }
    return (Join-Path $env:USERPROFILE "source\repos")
}

$resolvedRoot = Get-PwshRepoRoot -RepoRoot $RepoRoot
Write-Host "Repo root: $resolvedRoot"
New-Item -ItemType Directory -Force -Path $resolvedRoot | Out-Null

# Clone azure-powershell as "pwsh"
$pwshPath = Join-Path $resolvedRoot "pwsh"
if (-not (Test-Path $pwshPath)) {
    Invoke-NativeCommand -FilePath "git" `
        -Arguments @("clone", "https://github.com/Azure/azure-powershell.git", $pwshPath) `
        -Description "Cloning azure-powershell into $pwshPath"
} else {
    if (-not (Test-Path (Join-Path $pwshPath ".git"))) {
        throw "Path exists but is not a git repo: $pwshPath"
    }
    Write-Host "Repo already exists: $pwshPath"
}

# Clone swagger repo (shared with cdn-cli) for diff support
$swaggerPath = Join-Path $resolvedRoot "swagger"
if (-not $SkipSwagger) {
    if (-not (Test-Path $swaggerPath)) {
        Invoke-NativeCommand -FilePath "git" `
            -Arguments @("clone", "https://github.com/Azure/azure-rest-api-specs.git", $swaggerPath) `
            -Description "Cloning azure-rest-api-specs into $swaggerPath"
    } else {
        Write-Host "Swagger repo already exists: $swaggerPath"
    }
}

# Set environment variables
$env:PWSH_REPO_PATH = $pwshPath
$env:AAZ_SWAGGER_PATH = $swaggerPath

Write-Host ""
Write-Host "Initialization complete."
Write-Host "  PowerShell repo: $pwshPath"
if (-not $SkipSwagger) {
    Write-Host "  Swagger repo:    $swaggerPath"
}
Write-Host ""
Write-Host "Activate in new terminals:"
Write-Host "  . .github\cdn-pwsh\scripts\use_pwsh_env.ps1"
