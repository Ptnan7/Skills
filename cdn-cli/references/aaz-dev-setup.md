# AAZ-Dev Setup and Code Generation

> **CRITICAL**: ALL Python commands (`python`, `pip`, `aaz-dev`, scripts) MUST run inside the azdev virtual environment.
> The system Python does NOT have `requests`, `aaz-dev`, or CLI extensions installed.
> Always activate before any operation:
> ```powershell
> & C:\Users\jingnanxu\source\repos\azdev\Scripts\Activate.ps1
> ```

## Local Environment Setup

Environment variables required by `aaz-dev`:

| Env Var | Value | Purpose |
|---------|-------|---------|
| `AAZ_SWAGGER_PATH` | `C:\Users\jingnanxu\source\repos\swagger` | azure-rest-api-specs repo |
| `AAZ_PATH` | `C:\Users\jingnanxu\source\repos\aaz` | AAZ command model registry |
| `AAZ_CLI_PATH` | `C:\Users\jingnanxu\source\repos\cli` | azure-cli repo (shared context) |
| `AAZ_CLI_EXTENSION_PATH` | `C:\Users\jingnanxu\source\repos\extension` | azure-cli-extensions repo (primary output) |

**PowerShell activation:**

```powershell
# Activate virtual environment
& C:\Users\jingnanxu\source\repos\azdev\Scripts\Activate.ps1

# Set env vars
$env:AAZ_SWAGGER_PATH = "C:\Users\jingnanxu\source\repos\swagger"
$env:AAZ_PATH         = "C:\Users\jingnanxu\source\repos\aaz"
$env:AAZ_CLI_PATH     = "C:\Users\jingnanxu\source\repos\cli"
$env:AAZ_CLI_EXTENSION_PATH = "C:\Users\jingnanxu\source\repos\extension"

aaz-dev --version
```

**Install extension in editable mode if needed:**

```powershell
# CDN/AFD extension
Set-Location C:\Users\jingnanxu\source\repos\extension\src\cdn
pip install -e .

# Front Door extension
Set-Location C:\Users\jingnanxu\source\repos\extension\src\front-door
pip install -e .
```

---

## Code Generation — Preferred Path (Web UI)

Launch the web UI with all repo paths wired in:

```powershell
aaz-dev run `
  --swagger-path C:\Users\jingnanxu\source\repos\swagger `
  --aaz-path     C:\Users\jingnanxu\source\repos\aaz `
  --cli-path     C:\Users\jingnanxu\source\repos\cli `
  -e             C:\Users\jingnanxu\source\repos\extension
```

Opens at **http://127.0.0.1:5000**. Workflow:

1. **Workspace Editor** — select the CDN or Front Door spec, prune/rename the command surface, then click **EXPORT**
2. **CLI Generator** — select the extension target (`cdn` or `front-door`), review commands, click **GENERATE**

After generation, run `git status` in both `extension` and `aaz` to review changes.

**Restart aaz-dev** (e.g. after installing an extension with `pip install -e .`):

```powershell
& .github\skills\cdn-cli\scripts\restart_aaz_dev.ps1
```

This script kills the existing process on port 5000 and relaunches with all repo paths.

---

## Code Generation — Specific API Version

Check available swagger tags first:

```powershell
# CDN spec tags
Select-String `
  -Path    "C:\Users\jingnanxu\source\repos\swagger\specification\cdn\resource-manager\Microsoft.Cdn\Cdn\readme.md" `
  -Pattern "^### Tag:"

# Front Door spec tags
Select-String `
  -Path    "C:\Users\jingnanxu\source\repos\swagger\specification\frontdoor\resource-manager\Microsoft.Network\FrontDoor\readme.md" `
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
& C:\Users\jingnanxu\source\repos\azdev\Scripts\Activate.ps1

# --- CDN / AFD ---

# Dry run (see what would be selected)
python .github\skills\cdn-cli\scripts\auto_select_resources.py --ext cdn --version 2025-09-01-preview --dry-run

# Create workspace with resources
python .github\skills\cdn-cli\scripts\auto_select_resources.py --ext cdn --version 2025-09-01-preview

# Custom workspace name
python .github\skills\cdn-cli\scripts\auto_select_resources.py --ext cdn --version 2025-09-01-preview --workspace cdn-0901

# --- Front Door ---

# Dry run
python .github\skills\cdn-cli\scripts\auto_select_resources.py --ext front-door --version 2025-11-01 --dry-run

# Create workspace with resources
python .github\skills\cdn-cli\scripts\auto_select_resources.py --ext front-door --version 2025-11-01
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
| `front-door` | `front-door` | `Microsoft.Network` | `frontdoor` | `front-door-` |

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

- `aaz-dev` running: `aaz-dev run --swagger-path ... --aaz-path ... --cli-path ... -e ...`
- Virtual environment activated: `& C:\Users\jingnanxu\source\repos\azdev\Scripts\Activate.ps1`
- Local `azure-rest-api-specs` repo up to date with the new swagger version
- **Extension installed in azdev venv** (required for Web UI features like Add Example):
  ```powershell
  # Install if not already done — then restart aaz-dev
  Set-Location C:\Users\jingnanxu\source\repos\extension\src\front-door
  pip install -e .
  # or for CDN:
  Set-Location C:\Users\jingnanxu\source\repos\extension\src\cdn
  pip install -e .
  ```

### Step 1: Create working branches (Copilot or manual)

Create feature branches in both the `extension` and `aaz` repos before making any changes.

```powershell
# Branch in extension repo
Set-Location C:\Users\jingnanxu\source\repos\extension
git checkout -b <branch-name>   # e.g. front-door-2025-11-01, cdn-2025-09-01-preview

# Branch in aaz repo (Export writes here)
Set-Location C:\Users\jingnanxu\source\repos\aaz
git checkout -b <branch-name>
```

### Step 2: Compare swagger versions (Copilot)

Ask Copilot to diff the old vs new swagger. Provide the new swagger URL or local path. Key areas:
- New/removed operations, new enum values, new models
- LRO pattern changes (`final-state-via`)
- Breaking changes (removed fields, renamed properties)

### Step 3: Create workspace with auto-select script (Copilot)

```powershell
# CDN example:
python .github\skills\cdn-cli\scripts\auto_select_resources.py --ext cdn --version <new-version>

# Front Door example:
python .github\skills\cdn-cli\scripts\auto_select_resources.py --ext front-door --version <new-version>
```

The script creates a workspace, adds resources with inheritance, and generates swagger examples automatically.
If the new swagger adds new resources/operations not in AAZ, add them to the workspace (see "Adding new resources" above).

### Step 4: Review and export workspace (Manual — Web UI)

1. Open **http://127.0.0.1:5000**
2. Select the workspace (e.g. `front-door-2025-11-01`)
3. Review the command tree — verify commands, arguments, naming, and examples
4. Click **Export** to commit the command models (with examples) to the `aaz` repo
5. **Tell the agent** "已 Export" to proceed to CLI generation

> **Export must happen before CLI generation.** The Export writes examples into the `aaz` repo. CLI generation reads from `aaz`, so examples are only preserved if Export runs first.

### Step 5: Generate CLI code (Copilot)

After the user confirms Export is done, **first verify the aaz repo has changes** then generate:

```python
# 0. Verify Export happened — check aaz repo for uncommitted changes
#    Run: git status --short  in the aaz repo
#    If no changes → Export was not done, ask user to Export first

# 1. Read current CLI module, update all command versions, PUT back
data = requests.get("http://127.0.0.1:5000/CLI/Az/Extension/Modules/<ext-name>").json()
# ... update data['profiles']['latest'] command versions to new version ...
requests.put("http://127.0.0.1:5000/CLI/Az/Extension/Modules/<ext-name>", json=data)
```

This is safe because Export (Step 4) already wrote examples to `aaz`. The PUT reads examples from `aaz` when generating code.

> **Key constraint**: Always Export workspace FIRST (manual), then Generate CLI (automated). If you skip Export, examples will be lost.

### Step 6: Review generated changes (Manual, then tell agent)

User reviews the generated code diff. When satisfied, tells the agent to run tests.

```powershell
# Check extension repo changes
git diff --stat src/front-door/   # or src/cdn/
git diff src/front-door/

# Check aaz repo changes
Set-Location C:\Users\jingnanxu\source\repos\aaz
git status; git diff --stat
```

### Step 7: Run tests (Copilot — after user confirms review)

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

Bump the version in `setup.py` and add a changelog entry in `HISTORY.rst`.

```python
# setup.py — bump VERSION (minor for new features, patch for bugfixes)
VERSION = "X.Y.Z"

# HISTORY.rst — prepend new entry at the top (after the header)
# Format:
# X.Y.Z
# ++++++
# * Brief description of changes
```

Example for front-door:
- `setup.py`: `VERSION = "2.1.0"` → `"2.2.0"`
- `HISTORY.rst`: Add entry describing the swagger upgrade and new features

Example for cdn:
- `setup.py` at `src/cdn/setup.py`
- `HISTORY.rst` at `src/cdn/HISTORY.rst`

### Step 9: Commit to both repos (Copilot)

Commit changes in both `extension` and `aaz` repos on the feature branch.

```powershell
# Extension repo — commit AAZ code + WAF recordings + version bump + changelog
# Do NOT commit legacy test recordings (backend-pool, frontend-endpoint, etc.)
Set-Location C:\Users\jingnanxu\source\repos\extension
git add src/front-door/azext_front_door/aaz/
git add src/front-door/azext_front_door/tests/latest/recordings/test_waf_*.yaml
git add src/front-door/setup.py
git add src/front-door/HISTORY.rst
git commit -m "Upgrade front-door WAF policy commands to API version <version>"

# AAZ repo — commit all changes (hook will auto-verify command models)
Set-Location C:\Users\jingnanxu\source\repos\aaz
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
