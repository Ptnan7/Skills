# CDN Command Missing Target AAZ Model

## Symptom

CDN CLI generation fails after Export when `generate_cli.py --ext cdn --version <target-version>` PUTs the whole module. The failure points to a command that does not have an AAZ command model for the target API version.

This happens because the standard helper updates every `command.version` and `waitCommand.version` in the module, even if a command's markdown/model does not contain the target version.

## Rule

Do not blindly force every CDN/AFD command to the target API. Also do not immediately add every missing command to the pin list. A `Version '<target-version>' of command '<command>' not exist in AAZ` error often means the command is a property/subresource subcommand that should be regenerated for the target API first.

Before PUTing the module for CLI generation:

1. Check each generated command under `aaz/Commands/cdn/**/_*.md` and `aaz/Commands/afd/**/_*.md`.
2. Confirm it has a `### [<target-version>]` entry.
3. If the command markdown comment ends with a property path such as `properties.logScrubbing`, `properties.actions[]`, or `properties.conditions[]`, classify it as a property/subresource subcommand and follow `azure-cli-aaz-property-subcommands` to refresh or generate the command model for the target API.
4. For nested/property commands, confirm the linked target resource cfg contains the property and the generated command model or command group. If the target resource has the property but the command model is missing, prefer generating the target subcommand over pinning.
5. Pin only when the target swagger/resource cfg lacks the property, the AAZ generator cannot generate the subcommand correctly, or the command surface is intentionally not being refreshed in this upgrade.
6. After generation, scan old API references and confirm every hit is in the approved pin list.

Do not add a markdown-only version entry unless the linked resource cfg really contains the command model. A markdown entry without a real cfg command model can still fail generation.

## Property/Subresource Candidates To Regenerate Before Pinning

Maintain this list as CDN/AFD upgrades reveal property subcommands. When any of these fail with a missing target command model, check the target resource cfg and try the property-subcommand workflow before adding a pin.

| Command group | Parent resource | Property arg/path | Notes |
|---------------|-----------------|-------------------|-------|
| `afd profile log-scrubbing` | `/subscriptions/{}/resourcegroups/{}/providers/microsoft.cdn/profiles/{}` | `properties.logScrubbing` | Existing CLI may only register `show`; do not expose extra verbs unless requested. |
| `afd rule action` | `/subscriptions/{}/resourcegroups/{}/providers/microsoft.cdn/profiles/{}/rulesets/{}/rules/{}` | `properties.actions[]` / `$rule.properties.actions` | Refresh all registered verbs together. |
| `afd rule condition` | `/subscriptions/{}/resourcegroups/{}/providers/microsoft.cdn/profiles/{}/rulesets/{}/rules/{}` | `properties.conditions[]` / `$rule.properties.conditions` | Refresh all registered verbs together. |

For rule action/condition, AAZ subresource generation may default to `create/delete`. Existing CLI registration uses `add/remove`, so rename `create -> add` and `delete -> remove` before the first Export. If the wrong verbs were already exported, clean stale `_create.md`/`_delete.md` files and readme links, restart `aaz-dev`, then regenerate/rename in a fresh workspace. See `azure-cli-aaz-property-subcommands` for the full recovery flow.

## Known 2025-09-01-preview Pins

During the CDN `2025-09-01-preview` refresh, these commands intentionally stayed on older APIs:

| Command | Pinned API | Reason |
|---------|------------|--------|
| `afd profile log-scrubbing show` | `2025-06-01` | No `2025-09-01-preview` command model exists; the profile resource cfg contains `properties.logScrubbing` as a flat field but no nested `log-scrubbing` command group or command model. |

Expected non-target API hit after generation:

```text
extension\src\cdn\azext_cdn\aaz\latest\afd\profile\log_scrubbing\_show.py
```

## Known 2025-12-01 Pins

During the CDN stable `2025-12-01` refresh, these commands intentionally stayed on older APIs:

| Command | Pinned API | Reason |
|---------|------------|--------|
| `afd profile log-scrubbing show` | `2025-06-01` | The `2025-12-01` profile resource cfg has `properties.logScrubbing`, but no nested `log-scrubbing` command group/model. |
| `cdn profile deployment-version approve` | `2025-05-01-preview` | No `2025-12-01` command model. |
| `cdn profile deployment-version compare` | `2025-05-01-preview` | No `2025-12-01` command model. |
| `cdn profile deployment-version list` | `2025-05-01-preview` | No `2025-12-01` command model. |
| `cdn profile deployment-version show` | `2025-05-01-preview` | No `2025-12-01` command model. |
| `cdn profile deployment-version update` | `2025-05-01-preview` | No `2025-12-01` command model. |

## Validation

After generation, every non-target API hit under generated AAZ Python must be explainable by the approved pin list.

```powershell
$target = "2025-12-01"
$generatedRoot = "extension\src\cdn\azext_cdn\aaz\latest"

Get-ChildItem -Path $generatedRoot -Recurse -Filter "*.py" |
  Select-String -Pattern '"api-version", "([0-9]{4}-[0-9]{2}-[0-9]{2}(?:-preview)?)"' |
  Where-Object { $_.Matches[0].Groups[1].Value -ne $target }
```

For the 2025-12-01 refresh, the only expected files were:

```text
extension\src\cdn\azext_cdn\aaz\latest\afd\profile\log_scrubbing\_show.py
extension\src\cdn\azext_cdn\aaz\latest\cdn\profile\deployment_version\_approve.py
extension\src\cdn\azext_cdn\aaz\latest\cdn\profile\deployment_version\_compare.py
extension\src\cdn\azext_cdn\aaz\latest\cdn\profile\deployment_version\_list.py
extension\src\cdn\azext_cdn\aaz\latest\cdn\profile\deployment_version\_show.py
extension\src\cdn\azext_cdn\aaz\latest\cdn\profile\deployment_version\_update.py
```

Also run a syntax check. Prefer VS Code/Pylance diagnostics or a direct AST parse over terminal `compileall` during large generated diffs; `compileall` can be noisy in a persistent PowerShell session and should not be wrapped with `exit $LASTEXITCODE`.

```powershell
$code = @'
from pathlib import Path
import ast, sys
root = Path("extension/src/cdn/azext_cdn/aaz/latest")
errors = []
for path in root.rglob("*.py"):
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        errors.append(f"{path}:{exc.lineno}: {exc.msg}")
if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"syntax ok: {sum(1 for _ in root.rglob('*.py'))} files")
'@
python -c $code
if ($LASTEXITCODE -ne 0) { throw "Syntax check failed" }
```
