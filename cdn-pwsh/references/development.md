# Development

Covers what to do after a successful build: identifying cmdlet changes and keeping example documentation current.

---

## Analyze Module State (One Command)

Run `analyze_module.ps1` to get new cmdlets, removed cmdlets, and unfilled example placeholders in a single pass. Source of truth is `exports/` (populated by `build-module.ps1`); falls back to `examples/` with a warning if the module has not been built yet.

```powershell
. .github\cdn-pwsh\scripts\use_pwsh_env.ps1

# By module name (resolves src/<Module>/<Module>.Autorest or generated/<Module>/<Module>.Autorest)
& .github\cdn-pwsh\scripts\analyze_module.ps1 -Module Cdn
& .github\cdn-pwsh\scripts\analyze_module.ps1 -Module FrontDoor

# Or by explicit path
& .github\cdn-pwsh\scripts\analyze_module.ps1 -ModulePath C:\path\to\Cdn.Autorest
```

Output sections:

1. **New cmdlets (need tests)** — exported cmdlets with no matching `test/<Name>.Tests.ps1`. Confirm with the user which need tests.
2. **Removed cmdlets (test file orphaned)** — test files whose cmdlets are no longer exported. Confirm with the user which should be deleted, and also check `test/utils.ps1` and shared helpers for stale references before removing.
3. **Example files with unfilled placeholders** — `examples/*.md` still containing `{{ Add title here }}`, `{{ Add code here }}`, or `{{ Add description here }}`, reported with line numbers.

The script is read-only. Present results to the user and wait for approval before creating tests, deleting files, or editing examples.

---

## Update Example Documentation

For each new cmdlet, and for every file flagged in section 3 above:

1. Replace placeholders with real content:
   - A descriptive title
   - Working PowerShell code
   - Expected output
   - A brief description
2. Also scan existing `examples/*.md` for references to any removed parameters; update stale usage.
3. Show each change to the user and wait for approval before writing.
4. After examples are approved and written, inform the user you will rebuild docs with `pwsh -File ./build-module.ps1`. Wait for approval, then run.

---

## Approval Protocol

Always show the exact diff or file content before any of these, then wait for explicit approval:

- Creating new test files
- Editing example files
- Deleting orphaned test files
- Running `pwsh -File ./build-module.ps1` (doc rebuild)
