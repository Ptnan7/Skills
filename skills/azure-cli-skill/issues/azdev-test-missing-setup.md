# `azdev test` Cannot Find CLI Repo

## Symptom

`azdev test` fails with:

```text
Unable to retrieve CLI repo path from config
```

## Cause

The active azdev virtual environment has not been configured with the local Azure CLI and azure-cli-extensions repositories.

## Fix

Activate the shared `azdev` environment, then run setup once:

```powershell
. .github\skills\azure-cli-skill\scripts\use_aaz_dev_env.ps1
azdev setup -c cli -r extension
```

This persists for the venv across terminal sessions.

## Validation

Run the relevant target again:

```powershell
# CDN / AFD extension
azdev test cdn
azdev linter cdn

# Front Door maintained tests
azdev test test_waf_scenarios
azdev linter front-door
```
