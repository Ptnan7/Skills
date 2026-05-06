# CDN Command Missing Target AAZ Model

## Symptom

CDN CLI generation fails after Export when `generate_cli.py --ext cdn --version <target-version>` PUTs the whole module. The failure points to a command that does not have an AAZ command model for the target API version.

This happens because the standard helper updates every `command.version` and `waitCommand.version` in the module, even if a command's markdown/model does not contain the target version.

## Rule

Do not blindly force every CDN/AFD command to the target API. Before PUTing the module for CLI generation:

1. Check each generated command under `aaz/Commands/cdn/**/_*.md` and `aaz/Commands/afd/**/_*.md`.
2. Confirm it has a `### [<target-version>]` entry.
3. For nested/property commands, also confirm the linked resource cfg contains the actual command model or command group.
4. If the target model is missing, keep the command's existing working API version in the module payload.
5. After generation, scan old API references and confirm every hit is in the approved pin list.

Do not add a markdown-only version entry unless the linked resource cfg really contains the command model. A markdown entry without a real cfg command model can still fail generation.

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

Also run a syntax check:

```powershell
Push-Location extension\src\cdn
python -m compileall -q azext_cdn
Pop-Location
```
