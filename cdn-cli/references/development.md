# Development Patterns

## Adding a New Command in `src/cdn`

1. **Generate AAZ base**: Use `aaz-dev` to create or update the base command under `azext_cdn/aaz/latest/cdn/` or `azext_cdn/aaz/latest/afd/`
2. **Customize (optional)**: Subclass the AAZ base in `azext_cdn/custom/custom_cdn.py` or `azext_cdn/custom/custom_afdx.py`
3. **Register**: Import and assign in `azext_cdn/commands.py`
4. **Help text**: Add to `_help.py` using the `helps[...]` dict pattern
5. **Params**: Add to `_params.py` only if extra argument customization is needed beyond AAZ

---

## Updating AAZ Commands in `src/front-door`

1. Only edit files under `azext_front_door/aaz/latest/network/front_door/`
2. Use `aaz-dev` or the Web UI — do not hand-edit generated AAZ files
3. Do not touch `custom.py`, `custom_waf.py`, `vendored_sdks/`, `commands.py`, `_params.py`, or `_help.py` — these are legacy and not maintained

---

## AAZ Command Customization Pattern

```python
from azext_cdn.aaz.latest.afd.profile import Create as _AFDProfileCreate
from azure.cli.core.aaz import AAZStrArg, AAZBoolArg

class AFDProfileCreate(_AFDProfileCreate):
    @classmethod
    def _build_arguments_schema(cls, *args, **kwargs):
        args_schema = super()._build_arguments_schema(*args, **kwargs)
        args_schema.location._registered = False  # Hide argument
        return args_schema

    def pre_operations(self):
        self.ctx.args.location = 'global'  # Set fixed value
```

## Command Registration Pattern

```python
# azext_cdn/commands.py
from .custom.custom_cdn import CDNProfileCreate
self.command_table['cdn profile create'] = CDNProfileCreate(loader=self)
```

## Help Text Pattern

```python
# azext_cdn/_help.py
helps['cdn profile create'] = """
type: command
short-summary: Create a new CDN profile.
parameters:
  - name: --sku
    type: string
    short-summary: The pricing tier (e.g. Standard_Microsoft, Standard_AzureFrontDoor).
examples:
  - name: Create a CDN profile.
    text: az cdn profile create -g myRG -n myProfile --sku Standard_Microsoft
"""
```

---

## Linting

```bash
# src/cdn
azdev linter cdn

# src/front-door
azdev linter front-door
```

Exclusions for `src/cdn` live in `src/cdn/linter_exclusions.yml`.

---

## Common Pitfalls

- **CDN profile location** is always `'global'`. Set it in `pre_operations` and hide `--location` from the user.
- **`az afd ...` vs `az network front-door ...`**: these are separate extensions (`src/cdn` and `src/front-door`). Never mix their command tables or test suites.
- **AFD vs CDN param naming**: AFD commands typically use `--profile-name`; CDN commands may also accept `-n`. Check the existing parameter patterns before adding new ones.
- **Rule conditions/actions** in `src/cdn` have complex nested structures. Consult `custom/custom_rule_util.py` before adding or changing rule-related commands.
- **`src/front-door` legacy files**: if a legacy file appears to need a fix, do not modify it. Route the change through the AAZ-generated path or raise it as a known limitation.
