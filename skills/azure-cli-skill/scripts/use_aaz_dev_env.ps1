# Activate the shared azdev virtual environment and export repo paths.
# Run this in every new PowerShell terminal before Python or aaz-dev commands.

param(
    [string]$RepoRoot,
    [string]$VenvName = "azdev"
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "aaz_dev_common.ps1")

$context = Get-AazDevContext -RepoRoot $RepoRoot -VenvName $VenvName

if (-not (Test-Path $context.ActivatePath)) {
    throw "Virtual environment not found at $($context.VenvPath). Run initialize_aaz_dev_env.ps1 first."
}

. $context.ActivatePath
Set-AazDevEnvironment -Context $context

Write-Host "AAZ environment ready."
Write-Host "  Repo root: $($context.RepoRoot)"
Write-Host "  Swagger:   $($env:AAZ_SWAGGER_PATH)"
Write-Host "  AAZ:       $($env:AAZ_PATH)"
Write-Host "  CLI:       $($env:AAZ_CLI_PATH)"
Write-Host "  Extension: $($env:AAZ_CLI_EXTENSION_PATH)"