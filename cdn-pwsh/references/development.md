# Development

Covers what to do after a successful build: identifying cmdlet changes and keeping example documentation current.

---

## Identify New and Removed Cmdlets

After building the module (`exports/` is up to date):

1. Compare `exports/` with existing tests in `test/`.
2. Exported cmdlet with no matching `.Tests.ps1` → **new**.
3. Test file whose cmdlet is no longer in `exports/` → **removed**.
4. Present both lists and confirm with the user:
   - Which new cmdlets need tests
   - Whether orphaned test files for removed cmdlets should be deleted
5. For removed cmdlets, also check `test/utils.ps1` and shared helpers for stale references. Propose fixes and wait for approval before editing.

---

## Update Example Documentation

For each new cmdlet:

1. Search `examples/` for `{{ Add title here }}` or `{{ Add code here }}` placeholders.
2. Replace with real examples including:
   - A descriptive title
   - Working PowerShell code
   - Expected output
   - A brief description
3. Search existing `examples/*.md` for references to any removed parameters; update stale usage.
4. Show each change to the user and wait for approval before writing.
5. After examples are approved and written, inform the user you will rebuild docs with `pwsh -File ./build-module.ps1`. Wait for approval, then run.

---

## Approval Protocol

Always show the exact diff or file content before any of these, then wait for explicit approval:

- Editing example files
- Deleting orphaned test files
- Running `pwsh -File ./build-module.ps1` (doc rebuild)
