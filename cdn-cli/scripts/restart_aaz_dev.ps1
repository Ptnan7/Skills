# Restart aaz-dev web UI
# Kills the existing aaz-dev process on port 5000, then relaunches.
# Uses the shared azdev virtual environment and repo root.
#
# Usage:
#   & .github\cdn-cli\scripts\restart_aaz_dev.ps1
#
# Prerequisites:
#   - One-time setup completed: .github\cdn-cli\scripts\initialize_aaz_dev_env.ps1
#   - Repo root defaults to C:\Users\<User>\source\repos unless -RepoRoot is supplied

param(
    [string]$RepoRoot,
    [string]$VenvName = "azdev",
    [int]$Port = 5000,
    [string]$ListenHost = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "aaz_dev_common.ps1")

$context = Get-AazDevContext -RepoRoot $RepoRoot -VenvName $VenvName

if (-not (Test-Path $context.ActivatePath)) {
    throw "Virtual environment not found at $($context.VenvPath). Run initialize_aaz_dev_env.ps1 first."
}

. $context.ActivatePath
Set-AazDevEnvironment -Context $context

# Kill existing process on the port
$conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
if ($conn) {
    $pid = $conn.OwningProcess
    Write-Host "Stopping existing aaz-dev (PID $pid) on port $Port..."
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 1000
} else {
    Write-Host "No existing process on port $Port."
}

# Verify port is free
$conn2 = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($conn2) {
    Write-Error "Port $Port still in use. Kill the process manually."
    exit 1
}

foreach ($requiredPath in @($context.SwaggerPath, $context.AazPath, $context.CliPath, $context.ExtensionPath)) {
    if (-not (Test-Path $requiredPath)) {
        throw "Required path not found: $requiredPath. Run initialize_aaz_dev_env.ps1 first or supply -RepoRoot."
    }
}

Write-Host "Starting aaz-dev on http://${ListenHost}:${Port} ..."
aaz-dev run `
    --swagger-path $context.SwaggerPath `
    --aaz-path     $context.AazPath `
    --cli-path     $context.CliPath `
    -e             $context.ExtensionPath `
    --port         $Port
