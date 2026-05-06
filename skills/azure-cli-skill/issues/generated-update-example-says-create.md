# Generated Update Example Says Create

## Symptom

A generated `update` command has an example name or docstring that says `Create ...` / `Creates ...`.

Typical locations:

- generated Python docstrings in `_update.py`
- AAZ command markdown examples in `_update.md`

## Cause

Swagger `CreateOrUpdate` operations often share one `x-ms-examples` entry across both create and update commands. aaz-dev can reuse the create example text for the generated update command.

## Fix

Run generation without disabling the example fixer:

```powershell
python .github\skills\azure-cli-skill\scripts\generate_cli.py `
  --ext <cdn|front-door> `
  --version <api-version>
```

Do not pass `--no-fix-examples` unless intentionally preserving raw generated text.

If a case is not covered by the script, manually correct the example text to `Update ...` / `Updates ...` in the generated command docstring and AAZ markdown.

## Validation

Search generated update files for create wording:

```powershell
Get-ChildItem extension\src\<ext> -Recurse -Include *_update.py,*_update.md |
  Select-String -Pattern 'Create|Creates|create|creates'
```

Review each hit. Some text may legitimately describe a create-or-update REST operation, but command examples should match CLI command semantics.
