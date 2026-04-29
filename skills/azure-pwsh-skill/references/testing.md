# Testing

Covers adding Pester tests for new cmdlets, running tests, and merging split CRUD test files.

---

## Adding Tests for New Cmdlets

For each approved new cmdlet, create `test/<CmdletName>.Tests.ps1`. Adapt the `It` blocks to the parameter sets in the export file (`List`, `Get`, `GetViaIdentity`, `CreateExpanded`, `UpdateExpanded`, `Delete`, etc.):

```powershell
if(($null -eq $TestName) -or ($TestName -contains '<CmdletName>'))
{
  $loadEnvPath = Join-Path $PSScriptRoot 'loadEnv.ps1'
  if (-Not (Test-Path -Path $loadEnvPath)) {
      $loadEnvPath = Join-Path $PSScriptRoot '..\loadEnv.ps1'
  }
  . ($loadEnvPath)
  $TestRecordingFile = Join-Path $PSScriptRoot '<CmdletName>.Recording.json'
  $currentPath = $PSScriptRoot
  while(-not $mockingPath) {
      $mockingPath = Get-ChildItem -Path $currentPath -Recurse -Include 'HttpPipelineMocking.ps1' -File
      $currentPath = Split-Path -Path $currentPath -Parent
  }
  . ($mockingPath | Select-Object -First 1).FullName
}

Describe '<CmdletName>' {
    It 'List' -skip {
        { throw [System.NotImplementedException] } | Should -Not -Throw
    }

    It 'Get' -skip {
        { throw [System.NotImplementedException] } | Should -Not -Throw
    }

    It 'GetViaIdentity' -skip {
        { throw [System.NotImplementedException] } | Should -Not -Throw
    }
}
```

Before creating each file:
1. Show the proposed content.
2. Explain which parameter sets drove the `It` blocks.
3. **Wait for approval.**

---

## Running Tests

1. Inform the user you are about to run `pwsh -File ./test-module.ps1 -Record`.
2. Wait for approval.
3. Run the tests.
4. If tests fail:
   - Analyze the failure.
   - Propose the smallest fix scoped only to files inside the module directory.
   - Show the proposed edit and wait for approval.
   - Apply, then re-run.
5. If Azure connectivity is unavailable, suggest `-Playback` to validate test structure only.

---

## Merging CRUD Tests

Consolidate separate `Get/Update/Remove/Start/Stop` test files into a single `New-*` scenario file per resource.

### Target File Pattern

```powershell
if(($null -eq $TestName) -or ($TestName -contains 'New-Az<Resource>'))
{
  $loadEnvPath = Join-Path $PSScriptRoot 'loadEnv.ps1'
  if (-Not (Test-Path -Path $loadEnvPath)) {
      $loadEnvPath = Join-Path $PSScriptRoot '..\loadEnv.ps1'
  }
  . ($loadEnvPath)
  $TestRecordingFile = Join-Path $PSScriptRoot 'New-Az<Resource>.Recording.json'
  $currentPath = $PSScriptRoot
  while(-not $mockingPath) {
      $mockingPath = Get-ChildItem -Path $currentPath -Recurse -Include 'HttpPipelineMocking.ps1' -File
      $currentPath = Split-Path -Path $currentPath -Parent
  }
  . ($mockingPath | Select-Object -First 1).FullName
}

Describe 'New-Az<Resource>' {
    It 'CreateExpanded' {
        # New   - create resource with all interesting parameters
        # Get   - List, by name, ViaIdentity
        # Update - direct, ViaIdentity
        # Stop/Start (if applicable)
        # Remove - with PassThru
    }
}
```

### Rules

1. Keep the `Describe 'New-Az<Resource>'` name unchanged — renaming breaks test discovery.
2. Use a single `It 'CreateExpanded'` block for the full ordered scenario.
3. Create the resource and any sub-resources inline. Reuse `$env.ResourceGroupName` and shared profile names from environment setup, but do not rely on pre-created sub-resources unless the suite already standardises them.
4. Test each feature during the main create or update flow — avoid creating a second resource just to test a variation that fits in the primary flow.
5. Operation order: **New → Get list → Get by name → Get ViaIdentity → Update direct → Update ViaIdentity → Stop/Start → Remove** (with PassThru).
6. Remove is always last.

### Merge Groups

#### CDN Resources

| Target File | Merge From |
|-------------|------------|
| New-AzCdnProfile | Get, Update, Remove |
| New-AzCdnEndpoint | Get, Update, Remove, Start, Stop |
| New-AzCdnOrigin | Get, Update, Remove |
| New-AzCdnOriginGroup | Get, Update, Remove |
| New-AzCdnCustomDomain | Get, Remove, Enable/Disable-AzCdnCustomDomainCustomHttps |
| New-AzCdnPolicy | Get, Update, Remove |
| New-AzCdnProfileAgent | Get, Update, Remove |
| New-AzCdnWebAgent | Get, Update, Remove |
| New-AzCdnKnowledgeSource | Get, Update, Remove, Clear |
| New-AzCdnDeploymentVersion | Get, Update, Approve, Compare |

#### Front Door CDN Resources

| Target File | Merge From |
|-------------|------------|
| New-AzFrontDoorCdnProfile | Get, Update, Remove |
| New-AzFrontDoorCdnEndpoint | Get, Update, Remove |
| New-AzFrontDoorCdnOrigin | Get, Update, Remove |
| New-AzFrontDoorCdnOriginGroup | Get, Update, Remove |
| New-AzFrontDoorCdnCustomDomain | Get, Update, Remove |
| New-AzFrontDoorCdnRoute | Get, Update, Remove |
| New-AzFrontDoorCdnRule | Get, Update, Remove |
| New-AzFrontDoorCdnRuleSet | Get, Remove |
| New-AzFrontDoorCdnSecret | Get, Update, Remove |
| New-AzFrontDoorCdnSecurityPolicy | Get, Update, Remove |

#### Migration

| Target File | Merge From |
|-------------|------------|
| Test-AzFrontDoorCdnProfileMigration | Enable, Stop |

### Execution Steps

1. Identify the target `New-*` file and all source CRUD files for one resource.
2. Read the existing `New-*` file; preserve setup and assertions that still matter.
3. Fold coverage from `Get`, `Update`, `Remove`, `Start`, `Stop`, and companion tests into the single ordered scenario.
4. Show the merged test diff. **Wait for approval before writing.**
5. After writing, show the exact list of superseded `.Tests.ps1` and `.Recording.json` files to delete. **Wait for approval before deleting.**
6. Inform the user you will run `./test-module.ps1 -Record`. **Wait for approval**, then run to regenerate recordings.

### Keep These As-Is

Do not merge unless the user explicitly asks:

- `New-Az*Object.Tests.ps1` — in-memory object cmdlets, no Azure resources
- Single-verb cmdlets (`Test-*`, `Invoke-*`, `Move-*`, `Clear-*`) without a CRUD counterpart
- `Get-Az*ResourceUsage.Tests.ps1` — read-only usage queries
