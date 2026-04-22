# Summarize module state after an AutoRest build: new cmdlets, removed cmdlets, and example docs
# that still contain `{{ Add title here }}` / `{{ Add code here }}` placeholders.
#
# Covers development.md "Identify New and Removed Cmdlets" + "Update Example Documentation"
# in a single read-only command.
#
# Module path resolution order:
#   1. -ModulePath <path>
#   2. $env:PWSH_REPO_PATH\src\<Module>\<Module>.Autorest
#   3. $env:PWSH_REPO_PATH\generated\<Module>\<Module>.Autorest
#
# Usage:
#   & .github\cdn-pwsh\scripts\analyze_module.ps1 -Module Cdn
#   & .github\cdn-pwsh\scripts\analyze_module.ps1 -Module FrontDoor
#   & .github\cdn-pwsh\scripts\analyze_module.ps1 -ModulePath C:\path\to\Cdn.Autorest
#
# Exit codes:
#   0 — analysis completed (even if new/removed cmdlets exist; this is informational)
#   1 — module path cannot be resolved

param(
    [string]$Module,
    [string]$ModulePath
)

$ErrorActionPreference = "Stop"

function Resolve-AutorestDir {
    param(
        [string]$Module,
        [string]$ModulePath
    )

    if ($ModulePath) {
        if (-not (Test-Path $ModulePath)) {
            throw "ModulePath does not exist: $ModulePath"
        }
        return (Resolve-Path $ModulePath).Path
    }

    if (-not $Module) {
        throw "Provide -Module <Name> or -ModulePath <path>."
    }

    if (-not $env:PWSH_REPO_PATH) {
        throw "PWSH_REPO_PATH is not set. Run: . .github\cdn-pwsh\scripts\use_pwsh_env.ps1"
    }

    $candidates = @(
        (Join-Path $env:PWSH_REPO_PATH "src\$Module\$Module.Autorest"),
        (Join-Path $env:PWSH_REPO_PATH "generated\$Module\$Module.Autorest")
    )

    foreach ($c in $candidates) {
        if (Test-Path $c) { return (Resolve-Path $c).Path }
    }

    throw "Could not find <$Module>.Autorest under $env:PWSH_REPO_PATH. Tried:`n  $($candidates -join "`n  ")"
}

function Get-CmdletsFromFiles {
    param(
        [string]$Dir,
        [string]$Suffix  # e.g. '.ps1' for exports, '.Tests.ps1' for tests, '.md' for examples
    )

    if (-not (Test-Path $Dir)) { return @() }
    $files = Get-ChildItem -Path $Dir -Filter "*$Suffix" -File -ErrorAction SilentlyContinue
    $names = @()
    foreach ($f in $files) {
        # Strip the suffix (case-insensitive)
        $name = $f.Name
        if ($name.ToLower().EndsWith($Suffix.ToLower())) {
            $name = $name.Substring(0, $name.Length - $Suffix.Length)
        }
        $names += $name
    }
    return ,($names | Sort-Object -Unique)
}

$autorestDir = Resolve-AutorestDir -Module $Module -ModulePath $ModulePath
$exportsDir  = Join-Path $autorestDir "exports"
$testDir     = Join-Path $autorestDir "test"
$examplesDir = Join-Path $autorestDir "examples"

Write-Host "Module directory: $autorestDir"
Write-Host ""

# --- Source of truth for "current cmdlet list" ---
# Prefer exports/ (populated by build-module.ps1). Fall back to examples/ if the module has not been built yet.
$exportCmdlets = Get-CmdletsFromFiles -Dir $exportsDir -Suffix ".ps1"
$testCmdlets   = Get-CmdletsFromFiles -Dir $testDir    -Suffix ".Tests.ps1"
$exampleCmdlets = Get-CmdletsFromFiles -Dir $examplesDir -Suffix ".md"

$source = "exports/"
$currentCmdlets = $exportCmdlets
if ($exportCmdlets.Count -eq 0) {
    Write-Warning "exports/ is empty or missing; using examples/ as the cmdlet list. Run build-module.ps1 to refresh exports/."
    $currentCmdlets = $exampleCmdlets
    $source = "examples/ (exports/ unavailable)"
}

Write-Host "Cmdlet source: $source"
Write-Host "  current cmdlets: $($currentCmdlets.Count)"
Write-Host "  test files:      $($testCmdlets.Count)"
Write-Host "  example files:   $($exampleCmdlets.Count)"
Write-Host ""

# --- New / Removed cmdlets ---
$newCmdlets     = @($currentCmdlets | Where-Object { $testCmdlets -notcontains $_ })
$removedCmdlets = @($testCmdlets    | Where-Object { $currentCmdlets -notcontains $_ })

Write-Host "New cmdlets (need tests) [$($newCmdlets.Count)]:"
if ($newCmdlets.Count -eq 0) {
    Write-Host "  (none)"
} else {
    foreach ($c in $newCmdlets) { Write-Host "  + $c" }
}
Write-Host ""

Write-Host "Removed cmdlets (test file orphaned) [$($removedCmdlets.Count)]:"
if ($removedCmdlets.Count -eq 0) {
    Write-Host "  (none)"
} else {
    foreach ($c in $removedCmdlets) { Write-Host "  - $c" }
}
Write-Host ""

# --- Example placeholders ---
$placeholderRegex = '\{\{\s*Add\s+(title|code|description)[^\}]*\}\}'
$placeholderFiles = @{}
if (Test-Path $examplesDir) {
    $matches = Select-String -Path (Join-Path $examplesDir "*.md") -Pattern $placeholderRegex -ErrorAction SilentlyContinue
    foreach ($m in $matches) {
        $key = $m.Path
        if (-not $placeholderFiles.ContainsKey($key)) {
            $placeholderFiles[$key] = @()
        }
        $placeholderFiles[$key] += "L$($m.LineNumber): $($m.Line.Trim())"
    }
}

Write-Host "Example files with unfilled placeholders [$($placeholderFiles.Count)]:"
if ($placeholderFiles.Count -eq 0) {
    Write-Host "  (none)"
} else {
    foreach ($path in ($placeholderFiles.Keys | Sort-Object)) {
        $rel = $path.Substring($autorestDir.Length).TrimStart('\','/')
        Write-Host "  $rel"
        foreach ($line in $placeholderFiles[$path]) {
            Write-Host "    $line"
        }
    }
}
