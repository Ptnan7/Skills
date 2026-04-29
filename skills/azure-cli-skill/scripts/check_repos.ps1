# Verify that the four AAZ development repos exist under the resolved repo root.
# Lightweight — does not clone, does not activate the venv.
# Exit code 0 = all present; 1 = one or more missing.
#
# Usage:
#   & .github\skills\azure-cli-skill\scripts\check_repos.ps1
#   & .github\skills\azure-cli-skill\scripts\check_repos.ps1 -RepoRoot C:\path\to\repos
#   & .github\skills\azure-cli-skill\scripts\check_repos.ps1 -Quiet

param(
    [string]$RepoRoot,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "aaz_dev_common.ps1")

$resolvedRoot = Get-AazDevRepoRoot -RepoRoot $RepoRoot

if (-not $Quiet) {
    Write-Host "Repo root: $resolvedRoot"
}

$missing = @()
foreach ($repoName in $script:AazDevRequiredRepos) {
    $path = Join-Path $resolvedRoot $repoName
    $exists = Test-Path $path
    $isGit = $exists -and (Test-AazDevGitRepo -Path $path)

    if (-not $Quiet) {
        $status = if ($isGit) { "ok" } elseif ($exists) { "exists but not a git repo" } else { "missing" }
        Write-Host ("  {0,-10} {1}  [{2}]" -f $repoName, $path, $status)
    }

    if (-not $isGit) {
        $missing += $repoName
    }
}

if ($missing.Count -gt 0) {
    Write-Error ("Missing or invalid repos: {0}. Run initialize_aaz_dev_env.ps1 to bootstrap." -f ($missing -join ", "))
    exit 1
}

if (-not $Quiet) {
    Write-Host "All four repos present."
}
exit 0
