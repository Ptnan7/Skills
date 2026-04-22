# AAZ-Dev Setup and Code Generation

> **CRITICAL**: ALL Python commands (`python`, `pip`, `aaz-dev`, scripts) MUST run inside the azdev virtual environment.
> The system Python does NOT have `requests`, `aaz-dev`, or CLI extensions installed.
> Preferred workspace is `C:\Users\<User>\source\repos\Toolings` with `.github` linked to `C:\Users\<User>\source\repos\Skills`.
> Repo root is auto-detected from the current workspace; if detection fails, the fallback is `C:\Users\<User>\source\repos`.
> Run one-time initialization first, then activate the shared environment in every new terminal:
> ```powershell
> & .github\cdn-cli\scripts\initialize_aaz_dev_env.ps1
> . .github\cdn-cli\scripts\use_aaz_dev_env.ps1
> ```

## Local Environment Setup

## Toolings Workspace Layout

Create the Toolings workspace once, then open `Toolings` in VS Code:

```powershell
$repoRoot = Join-Path $env:USERPROFILE "source\repos"
$toolingsPath = Join-Path $repoRoot "Toolings"
$skillsPath = Join-Path $repoRoot "Skills"
$githubPath = Join-Path $toolingsPath ".github"

New-Item -ItemType Directory -Force -Path $toolingsPath | Out-Null
if (-not (Test-Path $githubPath)) {
  New-Item -ItemType Junction -Path $githubPath -Target $skillsPath | Out-Null
}
```

After that, all skill commands below assume the current workspace is `Toolings`.

One-time bootstrap:

```powershell
& .github\cdn-cli\scripts\initialize_aaz_dev_env.ps1 -PersistUserRepoRoot
```

If the venv or any of the four repos (`extension`, `swagger`, `aaz`, `cli`) is missing, the bootstrap script creates the missing pieces.

To verify the four repos exist **without** triggering a clone or venv activation:

```powershell
& .github\cdn-cli\scripts\check_repos.ps1        # human-readable output
& .github\cdn-cli\scripts\check_repos.ps1 -Quiet # exit code only (0 ok, 1 missing)
```

For every new PowerShell terminal:

```powershell
. .github\cdn-cli\scripts\use_aaz_dev_env.ps1
aaz-dev --version
```

Environment variables required by `aaz-dev`:

| Env Var | Value | Purpose |
|---------|-------|---------|
| `AAZ_SWAGGER_PATH` | `<repo-root>\swagger` | azure-rest-api-specs repo |
| `AAZ_PATH` | `<repo-root>\aaz` | AAZ command model registry |
| `AAZ_CLI_PATH` | `<repo-root>\cli` | azure-cli repo (shared context) |
| `AAZ_CLI_EXTENSION_PATH` | `<repo-root>\extension` | azure-cli-extensions repo (primary output) |

**PowerShell activation:**

```powershell
. .github\cdn-cli\scripts\use_aaz_dev_env.ps1
aaz-dev --version
```

**Install extension in editable mode if needed:**

```powershell
# CDN/AFD extension
Set-Location $env:AAZ_CLI_EXTENSION_PATH\src\cdn
pip install -e .

# Front Door extension
Set-Location $env:AAZ_CLI_EXTENSION_PATH\src\front-door
pip install -e .
```

---

## Code Generation — Preferred Path (Web UI)

Launch (or relaunch) the web UI — activates the venv, verifies the four repos, frees port 5000, and starts `aaz-dev run` with all paths wired in:

```powershell
& .github\cdn-cli\scripts\restart_aaz_dev.ps1
```

Opens at **http://127.0.0.1:5000**. Workflow:

1. **Workspace Editor** — select the CDN or Front Door spec, prune/rename the command surface, then click **EXPORT**
2. **CLI Generator** — select the extension target (`cdn` or `front-door`), review commands, click **GENERATE**

After generation, run `git status` in both `extension` and `aaz` to review changes.

Re-run the same `restart_aaz_dev.ps1` after installing an extension with `pip install -e .` to pick up the new code.

---

## Code Generation — Specific API Version

Check available swagger tags first:

```powershell
$swaggerRoot = $env:AAZ_SWAGGER_PATH

# CDN spec tags
Select-String `
  -Path    (Join-Path $swaggerRoot "specification\cdn\resource-manager\Microsoft.Cdn\Cdn\readme.md") `
  -Pattern "^### Tag:"

# Front Door spec tags
Select-String `
  -Path    (Join-Path $swaggerRoot "specification\frontdoor\resource-manager\Microsoft.Network\FrontDoor\readme.md") `
  -Pattern "^### Tag:"
```

Use the Web UI workspace with the desired tag, or pass it directly via `generate-by-swagger-tag` if needed — but ensure the output targets `extension` not `cli`.

---

## What to Generate Where

| Target | aaz-dev output path |
|--------|-------------------|
| `az cdn ...` / `az afd ...` | `extension/src/cdn/azext_cdn/aaz/latest/cdn/` or `aaz/latest/afd/` |
| `az network front-door waf-policy` | `extension/src/front-door/azext_front_door/aaz/latest/network/front_door/waf_policy/` |

Do not generate into `src/front-door` legacy paths (`custom.py`, `vendored_sdks/`, etc.).

---

## Auto-select Resources Script

When creating a workspace with many resources, use the script to pre-select correct versions and inherit existing AAZ models. Supports both `cdn` and `front-door` extensions.

```powershell
# Requires aaz-dev web UI running on http://127.0.0.1:5000
# Must run from the azdev virtual environment:
. .github\cdn-cli\scripts\use_aaz_dev_env.ps1

# --- CDN / AFD ---

# Dry run (see what would be selected)
python .github\cdn-cli\scripts\auto_select_resources.py --ext cdn --version 2025-09-01-preview --dry-run

# Create workspace with resources
python .github\cdn-cli\scripts\auto_select_resources.py --ext cdn --version 2025-09-01-preview

# Custom workspace name
python .github\cdn-cli\scripts\auto_select_resources.py --ext cdn --version 2025-09-01-preview --workspace cdn-0901

# --- Front Door ---

# Dry run
python .github\cdn-cli\scripts\auto_select_resources.py --ext front-door --version 2025-11-01 --dry-run

# Create workspace with resources
python .github\cdn-cli\scripts\auto_select_resources.py --ext front-door --version 2025-11-01
```

The script:
1. Queries the swagger spec for all resources under the RP
2. Checks the AAZ registry for existing command models (inheritance)
3. Selects the target version if available, otherwise inherits from the latest AAZ version
4. Creates a workspace and adds all selected resources via the aaz-dev API
5. New resources without AAZ history are **skipped** — add them manually in the Web UI after creation

**Extension profiles** (in `auto_select_resources.py` → `EXTENSION_PROFILES`):

| Extension | `mod_names` | `rp_name` | Swagger module | Workspace prefix |
|-----------|-------------|-----------|----------------|-----------------|
| `cdn` | `cdn` | `Microsoft.Cdn` | `cdn` | `cdn-` |
| `front-door` | `frontdoor` | `Microsoft.Network` | `frontdoor` | `front-door-` |

**Adding new resources not in AAZ** (e.g. a new operation added in the swagger):

```python
# After the script creates the workspace, add new resources via API:
import requests
payload = {
    'module': 'frontdoor',  # swagger module name, NOT mod_names
    'version': '2025-11-01',
    'resources': [
        {'id': '/subscriptions/{}/providers/microsoft.network/frontdoorwebapplicationfirewallpolicies'}
    ]
}
requests.post(
    'http://127.0.0.1:5000/AAZ/Editor/Workspaces/<workspace-name>/CommandTree/Nodes/aaz/AddSwagger',
    json=payload
)
```

Or add them via the Web UI **Workspace Editor** → **Add Swagger Resources**.

---

## Swagger Upgrade Workflow (End-to-End)

Complete steps to upgrade an extension from one API version to another.

### Prerequisites

- `aaz-dev` running: `& .github\cdn-cli\scripts\restart_aaz_dev.ps1`
- Virtual environment activated: `. .github\cdn-cli\scripts\use_aaz_dev_env.ps1`
- Local `azure-rest-api-specs` repo up to date with the new swagger version
- **Extension installed in azdev venv** (required for Web UI features like Add Example):
  ```powershell
  # Install if not already done — then restart aaz-dev
  Set-Location $env:AAZ_CLI_EXTENSION_PATH\src\front-door
  pip install -e .
  # or for CDN:
  Set-Location $env:AAZ_CLI_EXTENSION_PATH\src\cdn
  pip install -e .
  ```

### Step 1: Create working branches (Copilot or manual)

Create feature branches in both the `extension` and `aaz` repos before making any changes.

```powershell
# Branch in extension repo
Set-Location $env:AAZ_CLI_EXTENSION_PATH
git checkout -b <branch-name>   # e.g. front-door-2025-11-01, cdn-2025-09-01-preview

# Branch in aaz repo (Export writes here)
Set-Location $env:AAZ_PATH
git checkout -b <branch-name>
```

### Step 2: Compare swagger versions (Copilot)

Run the swagger diff script to compare old vs new versions:

```powershell
# Front Door example
python .github\cdn-cli\scripts\swagger_diff.py --ext front-door --old <old-version> --new <new-version>

# CDN example
python .github\cdn-cli\scripts\swagger_diff.py --ext cdn --old <old-version> --new <new-version>
```

The script parses the swagger `readme.md`, loads all JSON files for each tag, and reports:
- New/removed/modified operations
- New/removed/modified models and properties
- Enum value changes
- Breaking changes summary

Review the output before proceeding. Key areas to watch:
- LRO pattern changes (`final-state-via`)
- Breaking changes (removed fields, renamed properties)

To find the current API version in use, grep the AAZ-generated files:
```powershell
Get-ChildItem -Path "$env:AAZ_CLI_EXTENSION_PATH\src\front-door\azext_front_door\aaz\latest\" -Recurse -Filter "*.py" |
  Select-String -Pattern "api-version" | Select-Object -Property Line -Unique
```

### Step 3: Create workspace with auto-select script (Copilot)

```powershell
# CDN example:
python .github\cdn-cli\scripts\auto_select_resources.py --ext cdn --version <new-version>

# Front Door example:
python .github\cdn-cli\scripts\auto_select_resources.py --ext front-door --version <new-version>
```

The script creates a workspace, adds resources with inheritance, and generates swagger examples automatically.
The script also auto-fixes common swagger example issues (e.g. `update` commands inheriting a "Creates ..." example name from the shared `CreateOrUpdate` swagger operation — these are rewritten to "Updates ...").
If the new swagger adds new resources/operations not in AAZ, add them to the workspace (see "Adding new resources" above).

### Step 4: Review and export workspace (Manual or Copilot)

Option A — **Web UI** (manual):
1. Open **http://127.0.0.1:5000**
2. Select the workspace (e.g. `front-door-2025-11-01`)
3. Review the command tree — verify commands, arguments, naming, and examples
4. Click **Export** to commit the command models (with examples) to the `aaz` repo
5. **Tell the agent** "已 Export" to proceed to CLI generation

Option B — **API** (Copilot can do this automatically). Use `generate_cli.py --workspace <ws-name>` to Export and generate in a single call (see Step 5). To Export only, without generating, call the Generate endpoint directly:

```python
requests.post("http://127.0.0.1:5000/AAZ/Editor/Workspaces/<ws-name>/Generate")
```

This is equivalent to clicking Export in the Web UI — it writes command models and examples to the `aaz` repo.

> **Export must happen before CLI generation.** The Export writes examples into the `aaz` repo. CLI generation reads from `aaz`, so examples are only preserved if Export runs first.

### Step 5: Generate CLI code (Copilot)

After Export is done, **first verify the aaz repo has changes** (`git -C $env:AAZ_PATH status --short` must be non-empty), then generate. The script walks `profiles.latest`, bumps every `command.version` and `waitCommand.version` to the target, and PUTs the module back — which triggers CLI code generation.

```powershell
# Front Door
python .github\cdn-cli\scripts\generate_cli.py --ext front-door --version 2025-11-01

# CDN / AFD
python .github\cdn-cli\scripts\generate_cli.py --ext cdn --version 2025-09-01-preview

# Optional: Export the workspace first (same as clicking Export in Web UI), then generate
python .github\cdn-cli\scripts\generate_cli.py --ext front-door --version 2025-11-01 --workspace front-door-2025-11-01

# Dry run — show what would change without PUTing
python .github\cdn-cli\scripts\generate_cli.py --ext cdn --version 2025-09-01-preview --dry-run
```

This is safe because Export already wrote examples to `aaz`. The PUT reads examples from `aaz` when generating code.

> **Key constraint**: Always Export workspace FIRST, then Generate CLI. If you skip Export, examples will be lost. `--workspace` does the Export as part of the same command.

### Step 6: Review generated changes (Manual, then tell agent)

User reviews the generated code diff. When satisfied, tells the agent to run tests.

```powershell
# Check extension repo changes
git diff --stat src/front-door/   # or src/cdn/
git diff src/front-door/

# Check aaz repo changes
Set-Location $env:AAZ_PATH
git status; git diff --stat
```

**Common issues to look for in generated code:**

| Issue | Where to check | Fix |
|-------|---------------|-----|
| `update` command example says "Creates ..." | `:example:` docstring in `_update.py` | Change to "Updates ..." — swagger `CreateOrUpdate` shares one example across `create`/`update` |
| Example name doesn't match command semantics | `:example:` docstrings in all generated `*.py` | Manually correct; `auto_select_resources.py` auto-fixes common cases but not all |
| Missing examples | commands with no `:example:` | Add via Web UI or manually in the docstring |

### Step 7: Run tests (Copilot — after user confirms review)

**Prerequisite**: `azdev setup` must have been run to register CLI and extension repos. If `azdev test` fails with `Unable to retrieve CLI repo path from config`, run:
```powershell
azdev setup -c cli -r extension
```
This only needs to be done once per venv (it persists across terminal sessions).

Run only the relevant tests (WAF for front-door, or specific test files for cdn). Legacy front-door tests (backend-pool, frontend-endpoint, routing-rule, etc.) are not maintained and may fail — ignore those.

```powershell
# Front Door — run only WAF tests (maintained)
azdev test test_waf_scenarios

# CDN — run all
azdev test cdn

# Run linter
azdev linter front-door   # or cdn
```

### Step 8: Update extension version and changelog (Copilot)

Bump `setup.py` `VERSION` and prepend a `HISTORY.rst` entry. Supports both extensions and is idempotent (safe to re-run):

```powershell
# Front Door
python .github\cdn-cli\scripts\update_history.py --ext front-door --version 2.3.0 `
    --swagger-version 2025-11-01 `
    --message "Add support for managed rule set exceptions" `
    --message "Add new enum values: JA4 (MatchVariable), AsnMatch and ClientFingerprint (Operator)"

# CDN / AFD
python .github\cdn-cli\scripts\update_history.py --ext cdn --version 3.1.0 `
    --swagger-version 2025-09-01-preview `
    --message "Describe the user-facing change here"

# Preview only
python .github\cdn-cli\scripts\update_history.py --ext front-door --version 2.3.0 `
    --swagger-version 2025-11-01 --dry-run
```

The script writes to `extension/src/<ext>/setup.py` and `extension/src/<ext>/HISTORY.rst`. Version bump policy: **minor** for new features, **patch** for bugfixes.

### Step 9: Commit to both repos (Copilot)

Commit changes in both `extension` and `aaz` repos on the feature branch.

```powershell
# Extension repo — commit AAZ code + WAF recordings + version bump + changelog
# Do NOT commit legacy test recordings (backend-pool, frontend-endpoint, etc.)
Set-Location $env:AAZ_CLI_EXTENSION_PATH
git add src/front-door/azext_front_door/aaz/
git add src/front-door/azext_front_door/tests/latest/recordings/test_waf_*.yaml
git add src/front-door/setup.py
git add src/front-door/HISTORY.rst
git commit -m "Upgrade front-door WAF policy commands to API version <version>"

# AAZ repo — commit all changes (hook will auto-verify command models)
Set-Location $env:AAZ_PATH
git add -A
git commit -m "Upgrade front-door WAF policy command models to <version>"
```

> **Note**: The aaz repo has a pre-commit hook that runs `aaz-dev command-model verify`. This requires `aaz-dev` to be available in PATH (azdev venv). The hook may take 10-30 seconds — do not interrupt it.

Docs: [Workspace Editor](https://azure.github.io/aaz-dev-tools/pages/usage/workspace-editor/) · [CLI Generator](https://azure.github.io/aaz-dev-tools/pages/usage/cli-generator/) · [Customization](https://azure.github.io/aaz-dev-tools/pages/usage/customization/)

---

## AAZ Flow MCP Server

An MCP server at `tools/aaz-flow/` wraps aaz-dev as Copilot tools. Pre-configured in Codespace. Use cases:

- "generate code for azure cli" — generate models and code
- "generate test for cdn module" — generate test cases

---

## First-time Setup

```bash
uv pip install aaz-dev
git clone https://github.com/Azure/aaz.git
git clone https://github.com/Azure/azure-rest-api-specs.git
```
