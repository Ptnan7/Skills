# AAZ Export Skipped Before CLI Generation

## Symptom

Generated CLI code has missing or stale examples, or examples added in the aaz-dev workspace are not preserved in extension output.

## Cause

CLI generation reads command metadata and examples from the `aaz` repo. If the workspace is not exported first, examples that exist only in the local aaz-dev workspace are not available to the CLI generator.

## Fix

Export the workspace before CLI generation.

Manual path:

1. Open `http://127.0.0.1:5000`.
2. Select the workspace.
3. Review commands and examples.
4. Click **Export**.
5. Verify `git -C $env:AAZ_PATH status --short` is non-empty.
6. Generate CLI.

Scripted path:

```powershell
python .github\skills\azure-cli-skill\scripts\generate_cli.py `
  --ext <cdn|front-door> `
  --version <api-version> `
  --workspace <workspace-name>
```

The `--workspace` option exports first, then generates CLI.

## Rule

Always Export workspace first, then Generate CLI. If Export is skipped, examples can be lost.
