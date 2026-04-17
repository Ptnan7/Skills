# Activate the PowerShell module development environment.
# Sets env vars for the pwsh repo and swagger repo paths.
# Run this in every new PowerShell terminal before working on the module.

param(
    [string]$RepoRoot
)

$ErrorActionPreference = "Stop"

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

$pwshPath = Join-Path $resolvedRoot "pwsh"
$swaggerPath = Join-Path $resolvedRoot "swagger"

if (-not (Test-Path $pwshPath)) {
    throw "PowerShell repo not found at $pwshPath. Run initialize_pwsh_env.ps1 first."
}

$env:PWSH_REPO_PATH = $pwshPath
if (Test-Path $swaggerPath) {
    $env:AAZ_SWAGGER_PATH = $swaggerPath
}

Write-Host "PowerShell environment ready."
Write-Host "  Repo root:    $resolvedRoot"
Write-Host "  PowerShell:   $pwshPath"
if (Test-Path $swaggerPath) {
    Write-Host "  Swagger:      $swaggerPath"
}
