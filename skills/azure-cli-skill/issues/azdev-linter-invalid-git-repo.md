# azdev linter Fails with `invalid git repo: None`

## Symptom

`azdev linter cdn` (or `azdev linter front-door`) shows all lint rules passing, then exits with code 1 and logs:

  cli.knack.cli: invalid git repo: None

No useful diff analysis was requested; the failure happens in a git-diff-based post-processing step.

## Cause

The `missing_command_example` rule calls `diff_branch_file_patch(repo=None, ...)` after all static rules run.
When `--repo` is not supplied, `repo` is None, `git.Repo(None)` raises `InvalidGitRepositoryError`,
which knack catches and logs as `invalid git repo: None`.

This is NOT a CDN/AFD lint error. All static lint rules had already passed.

## Fix

### Option A -- Run only static rule types (recommended for swagger upgrades)

    azdev linter cdn -t help_entries command_groups commands params

This skips `command_test_coverage` (the group containing `missing_command_example`) entirely.

### Option B -- Supply git context

    azdev linter cdn --repo .\extension --tgt main --src <your-branch>

This enables the git-diff rules and avoids the None error.

## Notes

- Exit code is still 1 even though all rule results printed as `pass`.
  Use Option A or Option B to get a clean exit for CI.
- `azdev setup -c cli -r extension` must be run first (see azdev-test-missing-setup.md);
  otherwise the linter cannot load the command table at all.
