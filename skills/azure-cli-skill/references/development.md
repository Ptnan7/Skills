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
3. Do not touch `custom.py`, `custom_waf.py`, `vendored_sdks/`, `commands.py`, `_params.py`, or `_help.py` — these are legacy and not maintained. See [front-door-legacy-files-tests.md](../issues/front-door-legacy-files-tests.md).

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
- **CDN rule-set batch mode can need a local aaz-dev cfg patch**: if `cdn profile rule-set update` drops `rules[].ruleName` from `instanceUpdate`, patch only the `.aaz_dev` workspace cache before Export. See [cdn-ruleset-update-drops-rule-name.md](../issues/cdn-ruleset-update-drops-rule-name.md).
- **CDN swagger upgrades can require property subcommand regeneration**: if an existing nested/property command lacks a command model for the target API, load `azure-cli-aaz-property-subcommands` and recreate or refresh the target subcommand before regenerating CLI.
- **Custom args can conflict with new generated args**: when a swagger upgrade promotes a previously custom-only field into the generated schema, `_build_arguments_schema` overrides that re-define those args will raise `AAZConflictFieldDefinitionError`. Guard all custom arg additions with `getattr(args_schema, name)` + `except AAZUnknownFieldError` instead of direct assignment. Never use `'field_name' in args_schema`; `AAZArgumentsSchema.__contains__` raises `AAZUnknownFieldError: has no field named '0'`. See [cdn-custom-arg-conflicts-generated.md](../issues/cdn-custom-arg-conflicts-generated.md).
- **`azdev linter` may exit 1 even when all rules pass**: if run without `--repo/--tgt/--src`, the `missing_command_example` rule fails with `invalid git repo: None` after static rules complete. Use `-t help_entries command_groups commands params` to run only static rules, or supply git context. See [azdev-linter-invalid-git-repo.md](../issues/azdev-linter-invalid-git-repo.md).
- **`src/front-door` legacy files**: if a legacy file appears to need a fix, do not modify it. Route the change through the AAZ-generated path or raise it as a known limitation. See [front-door-legacy-files-tests.md](../issues/front-door-legacy-files-tests.md).
