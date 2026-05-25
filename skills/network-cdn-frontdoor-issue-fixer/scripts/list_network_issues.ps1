param(
    [ValidateSet("azure-cli", "azure-powershell", "All")]
    [string] $Repo = "azure-cli",

    [ValidateSet("Network - CDN", "Network - Front Door")]
    [string] $Label,

    [ValidateRange(1, 1000)]
    [int] $Limit = 100,

    [string] $OutJson
)

$ErrorActionPreference = "Stop"

$labels = if ($Label) {
    @($Label)
} else {
    @("Network - CDN", "Network - Front Door")
}

$repos = if ($Repo -eq "All") {
    @("Azure/azure-cli", "Azure/azure-powershell")
} else {
    @("Azure/$Repo")
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI 'gh' was not found. Install gh or use the GitHub issue tools/API directly."
}

$allIssues = foreach ($repoName in $repos) {
    foreach ($issueLabel in $labels) {
        $json = gh issue list `
            --repo $repoName `
            --state open `
            --label $issueLabel `
            --limit $Limit `
            --json number,title,url,labels,assignees,createdAt,updatedAt

        $issues = $json | ConvertFrom-Json
        foreach ($issue in $issues) {
            [pscustomobject]@{
                repo = $repoName
                label = $issueLabel
                number = $issue.number
                title = $issue.title
                url = $issue.url
                labels = @($issue.labels | ForEach-Object { $_.name })
                assignees = @($issue.assignees | ForEach-Object { $_.login })
                createdAt = $issue.createdAt
                updatedAt = $issue.updatedAt
            }
        }
    }
}

$sortedIssues = @($allIssues | Sort-Object repo, label, number)

if ($OutJson) {
    $parent = Split-Path -Parent $OutJson
    if ($parent -and -not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }
    $sortedIssues | ConvertTo-Json -Depth 6 | Set-Content -Path $OutJson -Encoding utf8
}

if ($sortedIssues.Count -eq 0) {
    Write-Output "No open issues found for repo '$Repo' with the selected label(s): $($labels -join ', ')"
    return
}

foreach ($group in ($sortedIssues | Group-Object repo, label)) {
    Write-Output ""
    Write-Output "## $($group.Group[0].repo) / $($group.Group[0].label) ($($group.Count))"
    foreach ($issue in $group.Group) {
        $labelText = ($issue.labels -join ", ")
        Write-Output "- #$($issue.number) $($issue.title)"
        Write-Output "  $($issue.url)"
        Write-Output "  Labels: $labelText"
        if ($issue.assignees.Count -gt 0) {
            Write-Output "  Assignees: $($issue.assignees -join ', ')"
        }
        Write-Output "  Updated: $($issue.updatedAt)"
    }
}
