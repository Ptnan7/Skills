# AutoRest Generation

Covers updating the AutoRest README config, running generation, and building the module.

---

## Inputs

Collect these if not already provided:

1. **Module name** — e.g. `Cdn`, `EventGrid`, `ContainerRegistry`
2. **Requested `README.md` changes** — new commit hash, swagger path, API version, or directives

Resolve the AutoRest project directory:

- `src/<Module>/<Module>.Autorest/` (primary)
- `generated/<Module>/<Module>.Autorest/` (some modules)

---

## Step 1: Update `.Autorest/README.md`

1. Read the current `README.md` in the `.Autorest` directory.
2. Prepare the exact requested changes — incorporating the new API version if one was identified via swagger diff.
3. Enforce these conventions:
   - Use commit hashes, never branch names, for API spec references.
   - Add a short comment explaining the purpose of each new directive.
4. Show the proposed diff to the user.
5. **Wait for approval before writing.**

---

## Step 2: Run AutoRest Generation

1. Inform the user you are about to run `autorest` from the `.Autorest` directory.
2. Wait for approval.
3. Run `autorest`.
4. If generation fails:
   - Analyze the error output.
   - Propose the smallest fix scoped to files inside the module directory only (e.g. `src/Cdn/`).
   - Explain why the fix is needed.
   - Show the proposed edit and wait for approval.
   - Apply, then re-run `autorest`.
   - Repeat until generation succeeds or a genuine blocker is found.

---

## Step 3: Build the Module

1. Inform the user you are about to run `pwsh -File ./build-module.ps1`.
2. Wait for approval.
3. Run `pwsh -File ./build-module.ps1`.
4. If the build fails, follow the same fix loop as Step 2.
5. After a successful build, record the exported cmdlets from `exports/`.

---

## Error-Fixing Rules

- **Scope**: only modify files inside the module's own directory (e.g. `src/Cdn/`)
- Never touch shared infrastructure, common build scripts, or other modules
- Prefer the smallest root-cause fix over broad cleanup
- Re-run the failed command after each approved fix to confirm it resolves the issue

Common valid fixes:

| Problem | Fix |
|---------|-----|
| Problematic cmdlet or model | Add/update `README.md` directives to rename, remove, or hide it |
| Custom cmdlet references changed types | Update `custom/` scripts |
| Model name change | Fix `no-inline` entries |
| Model shape change | Adjust `model-cmdlet` mappings |

---

## Approval Protocol

Always show the exact command or diff before any of these, then wait for explicit approval:

- Editing `README.md`
- Editing any source file to fix failures
- Running `autorest`
- Running `pwsh -File ./build-module.ps1`
