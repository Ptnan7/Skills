# Initialize local AAZ development dependencies.
#
# Default repo root: auto-detect from the current workspace, otherwise C:\Users\<User>\source\repos
# Creates missing repos, creates the azdev virtual environment,
# installs required Python packages, and wires environment variables.

param(
    [string]$RepoRoot,
    [string]$VenvName = "azdev",
    [switch]$SkipClone,
    [switch]$SkipPackageInstall,
    [switch]$SkipEditableExtensionInstall,
    [switch]$PersistUserRepoRoot
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "aaz_dev_common.ps1")

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

function Get-PythonBootstrapCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return [pscustomobject]@{ FilePath = "py"; Arguments = @("-3") }
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        return [pscustomobject]@{ FilePath = "python"; Arguments = @() }
    }

    throw "Python 3 was not found. Install Python 3 first, then rerun this script."
}

$context = Get-AazDevContext -RepoRoot $RepoRoot -VenvName $VenvName
$repoRootResolved = $context.RepoRoot

Write-Host "Repo root: $repoRootResolved"
if (-not $RepoRoot) {
    Write-Host "Repo root source: auto-detected from the current working directory (fallback is C:\Users\<User>\source\repos)."
}
New-Item -ItemType Directory -Force -Path $repoRootResolved | Out-Null

$repoMap = [ordered]@{
    extension = "https://github.com/Azure/azure-cli-extensions.git"
    swagger   = "https://github.com/Azure/azure-rest-api-specs.git"
    aaz       = "https://github.com/Azure/aaz.git"
    cli       = "https://github.com/Azure/azure-cli.git"
}

if (-not $SkipClone) {
    foreach ($repoName in $repoMap.Keys) {
        $targetPath = Join-Path $repoRootResolved $repoName
        $remote = $repoMap[$repoName]

        if (-not (Test-Path $targetPath)) {
            Invoke-NativeCommand -FilePath "git" -Arguments @("clone", $remote, $targetPath) -Description "Cloning $repoName into $targetPath"
            continue
        }

        if (-not (Test-AazDevGitRepo -Path $targetPath)) {
            throw "Path exists but is not a git repo: $targetPath"
        }

        Write-Host "Repo already exists: $targetPath"
    }
}

if (-not (Test-Path $context.VenvPath)) {
    $pythonCommand = Get-PythonBootstrapCommand
    $venvArgs = @()
    $venvArgs += $pythonCommand.Arguments
    $venvArgs += @("-m", "venv", $context.VenvPath)
    Invoke-NativeCommand -FilePath $pythonCommand.FilePath -Arguments $venvArgs -Description "Creating virtual environment at $($context.VenvPath)"
} else {
    Write-Host "Virtual environment already exists: $($context.VenvPath)"
}

if (-not (Test-Path $context.ActivatePath)) {
    throw "Activation script not found: $($context.ActivatePath)"
}

. $context.ActivatePath
Set-AazDevEnvironment -Context $context

if ($PersistUserRepoRoot) {
    [Environment]::SetEnvironmentVariable("AAZ_REPOS_ROOT", $repoRootResolved, "User")
    Write-Host "Persisted AAZ_REPOS_ROOT for the current user: $repoRootResolved"
}

if (-not $SkipPackageInstall) {
    Invoke-NativeCommand -FilePath "python" -Arguments @("-m", "pip", "install", "--upgrade", "pip") -Description "Upgrading pip"
    Invoke-NativeCommand -FilePath "python" -Arguments @("-m", "pip", "install", "requests", "aaz-dev", "azdev") -Description "Installing Python packages for AAZ work"
}

if (-not $SkipEditableExtensionInstall) {
    foreach ($extensionSubdir in @("src\cdn", "src\front-door")) {
        $editablePath = Join-Path $context.ExtensionPath $extensionSubdir
        if (Test-Path $editablePath) {
            Invoke-NativeCommand -FilePath "python" -Arguments @("-m", "pip", "install", "-e", $editablePath) -Description "Installing editable extension $editablePath"
        }
    }
}

Write-Host "Initialization complete."
Write-Host "Use these settings in new terminals:"
Write-Host "  Repo root: $repoRootResolved"
Write-Host "  Venv:      $($context.VenvPath)"
Write-Host "  Activate (Toolings workspace): . .github\cdn-cli\scripts\use_aaz_dev_env.ps1"
Write-Host "  Activate (direct path):        . $(Join-Path $PSScriptRoot 'use_aaz_dev_env.ps1')"