# AutoRest Generation

Covers updating the AutoRest README config, running generation, and building the module.

---

## Inputs

Collect these if not already provided:

1. **Module name** — e.g. `Cdn`, `EventGrid`, `ContainerRegistry`
2. **Requested `README.md` changes** — new commit hash, swagger path, API version, or directives

Resolve the AutoRest project directory (use `$env:PWSH_REPO_PATH` set by `use_pwsh_env.ps1`):

- `$env:PWSH_REPO_PATH\src\<Module>\<Module>.Autorest\` (primary)
- `$env:PWSH_REPO_PATH\generated\<Module>\<Module>.Autorest\` (some modules)

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

## Step 3: Review Custom Code

After autorest regeneration and before building, check whether hand-written code in `custom/` needs updating. This step prevents build failures and runtime bugs caused by stale references.

1. List all files in the `custom/` directory.
2. Cross-reference the swagger diff results (new/removed/modified models, renamed properties, changed enums) against the custom code.
3. For each custom file, check:
   - **Model/type references** — does the file construct or reference a model that was renamed, removed, or gained new required properties?
   - **Enum values** — does the file hardcode enum values that were removed or renamed?
   - **Parameter names** — does the file reference parameter names that changed due to property renames in the swagger?
4. Present findings to the user:
   - Files that need changes, with the specific lines and reason.
   - Files that are unaffected.
5. **Wait for approval before editing any custom file.**
6. If no changes are needed, inform the user and proceed to build.

Common patterns in `custom/` files:

| Pattern | What to check |
|---------|---------------|
| `New-Az*Object` wrappers | Do they pass through all properties? New required properties may need defaults or parameters. |
| `New-Az*` / `Update-Az*` cmdlets | Do they reference model types that were renamed or restructured? |
| `Set-Az*` / hidden cmdlet wrappers | Do they call generated cmdlets whose parameter sets changed? |

---

## Step 4: Build the Module

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

## Step 5: Run Tests

After a successful build, **ask the user whether to run unit tests**. Do not run tests automatically.

1. Inform the user the build succeeded and ask: "Build succeeded. Would you like to run the unit tests?"
2. If the user confirms, run `pwsh -File ./test-module.ps1 -Playback` from the `.Autorest/` directory.
3. If tests fail, analyze the failures and propose fixes (scoped to the module directory).
4. If the user declines, skip to the next step.

---

## Step 6: Commit

After tests pass (or were skipped), **ask the user whether to commit the changes**. Do not commit automatically.

1. Show a summary of changed files: `git status --short` in the `$env:PWSH_REPO_PATH` repo.
2. Ask the user: "Tests passed. Would you like to commit these changes?"
3. If the user confirms:
   - Stage all changes under `src/<Module>/`: `git add src/<Module>/`
   - Commit with a descriptive message, e.g.: `Upgrade FrontDoor module to API version 2025-11-01`
4. If the user declines, skip. Do not push — pushing is always a manual decision.

---

## Approval Protocol

Always show the exact command or diff before any of these, then wait for explicit approval:

- Editing `README.md`
- Editing any source file to fix failures
- Running `autorest`
- Running `pwsh -File ./build-module.ps1`
- Running `pwsh -File ./test-module.ps1`
- Committing changes (`git commit`)
