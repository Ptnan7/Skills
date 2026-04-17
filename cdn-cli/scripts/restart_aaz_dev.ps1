# Restart aaz-dev web UI
# Kills the existing aaz-dev process on port 5000, then relaunches.
# Must be run from the azdev virtual environment.
#
# Usage:
#   & .github\skills\cdn-cli\scripts\restart_aaz_dev.ps1
#
# Prerequisites:
#   - azdev venv activated: & C:\Users\jingnanxu\source\repos\azdev\Scripts\Activate.ps1
#   - Extensions installed: pip install -e src\front-door  (or src\cdn)

param(
    [int]$Port = 5000,
    [string]$Host = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

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

# Launch aaz-dev
$swaggerPath = "C:\Users\jingnanxu\source\repos\swagger"
$aazPath     = "C:\Users\jingnanxu\source\repos\aaz"
$cliPath     = "C:\Users\jingnanxu\source\repos\cli"
$extPath     = "C:\Users\jingnanxu\source\repos\extension"

Write-Host "Starting aaz-dev on http://${Host}:${Port} ..."
aaz-dev run `
    --swagger-path $swaggerPath `
    --aaz-path     $aazPath `
    --cli-path     $cliPath `
    -e             $extPath `
    --port         $Port
