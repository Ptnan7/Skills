---
name: azure-cli-test-skill
description: "Generate or update Azure CLI extension scenario tests after swagger/API/AAZ CLI changes. Use for az cdn, az afd, and az network front-door test work, especially when swagger diff or generated command changes require updating existing test files or creating new tests. Always starts with a subagent analysis and never runs tests without explicit user approval."
argument-hint: "Describe the API/version and test need, e.g. 'generate cdn 2025-12-01 tests' or 'update afd rule-set tests from swagger diff'"
---

# Azure CLI Test Generation

## Scope

Use this skill to create or update scenario tests for Azure edge CLI extensions:

- `extension/src/cdn/azext_cdn/tests/latest/` — `az cdn ...` and `az afd ...`
- `extension/src/front-door/azext_front_door/tests/latest/test_waf_scenarios.py` — maintained `az network front-door waf-policy ...` tests only

This skill is intentionally separate from swagger/AAZ generation. Swagger upgrade work may hand off here after CLI code is generated.

## Required Workflow

1. **Gather inputs.** Identify extension (`cdn` or `front-door`), old API version, new API version, the swagger diff output or command/resource area, and any generated CLI files already changed. If the task is a non-swagger custom-layer cleanup, identify the removed custom command overrides and the generated AAZ commands/arguments that now own the behavior.
2. **Run or read swagger diff when applicable.** If this is a swagger/API update and no diff is available, run the existing swagger diff helper from `azure-cli-skill` before deciding test coverage:
   ```powershell
   python .github\skills\azure-cli-skill\scripts\swagger_diff.py --ext <cdn|front-door> --old <old-version> --new <new-version>
   ```
   For non-swagger custom-layer cleanup, do not manufacture a swagger diff. Instead, inspect the code diff, generated AAZ schemas, command registrations, existing test commands, and mixin helpers. Treat generated AAZ schemas and generated command examples as authoritative; do not assume a removed flattened option has a one-for-one replacement unless the generated command actually exposes it.
3. **Launch a sub agent before editing.** Use `runSubagent` with `agentName: "Explore"` in read-only mode. The subagent must analyze the swagger diff or non-swagger code diff, generated command changes, existing test files, and mixins. It must return:
   - changed operations/models/properties/enums that need test coverage
   - impacted CLI commands and arguments
   - existing test file(s) to update, or why a new file is needed
   - mixin helper changes needed, if any
   - proposed test method names and scenario steps
   - exact test command(s) that could be run later, but do not run them
4. **Map diff to tests.** Use [test-generation.md](./references/test-generation.md) to decide whether to upgrade an existing test file or add a new file. For custom-layer cleanup, prefer updating existing mixin helpers so scenario intent remains stable while actual CLI invocations use generated AAZ object/list JSON arguments.
5. **Edit tests.** Keep changes focused on behavior introduced or changed by the swagger/API update or custom-layer cleanup. Prefer existing helpers and scenario style.
6. **Validate without running scenario tests.** Syntax-check edited Python and use diagnostics/lint-style checks when cheap. Do not run `azdev test` yet.
7. **Ask before running tests.** Use `vscode_askQuestions` and show the exact command(s), for example `azdev test test_afd_rule_crud --profile latest`. Only run tests after the user explicitly approves. If live mode or recording generation is needed, ask separately.

## Approved Test Run Pitfalls

When the user explicitly approves running one or more tests, use this checklist before interpreting failures:

1. **Activate the shared azdev environment in the same command/session.** Prefer:
   ```powershell
   . .github\skills\azure-cli-skill\scripts\use_aaz_dev_env.ps1
   .\azdev\Scripts\azdev.exe test <target> --profile latest
   ```
   Do not rely on global `azdev` from `AppData\Local\Programs\Python...\Scripts`; it can fail with `TypeError: _path_splitroot_ex: path should be string, bytes or os.PathLike, not NoneType` because `get_env_path()` is unset.
2. **Run setup once if azdev cannot resolve local repos.** If `azdev test` cannot find CLI/extension repo config, or the env has no active config, run after activation:
   ```powershell
   azdev setup -c cli -r extension
   ```
   Then retry the exact same test command.
3. **Use azdev discovery keys, not pytest `::` paths, for `<TESTS>`.** `azdev test` looks up method/class/file/module keys in its test index. Prefer selectors like `test_afd_rule_crud`, `CdnAfdRuleScenarioTest`, or `test_afd_rule_scenarios`. A raw pytest path such as `test_afd_rule_scenarios::CdnAfdRuleScenarioTest::test_afd_rule_crud` may be reported as not found.
4. **Refresh discovery when a selector is not found.** If `azdev test test_foo --profile latest` says the test is not found, retry once with `--discover`. If it is still not found, inspect the index with the venv Python before changing tests:
   ```powershell
    $idx = Get-ChildItem "$env:USERPROFILE\.azdev\env_config" -Recurse -Filter latest.json |
       Sort-Object LastWriteTime -Descending | Select-Object -First 1
    .\azdev\Scripts\python.exe -c "import json, pathlib, sys; d=json.loads(pathlib.Path(sys.argv[1]).read_text()); print([k for k in d if 'afd' in k.lower() or 'cdn' in k.lower()][:80])" $idx.FullName
   ```
5. **Expect quiet, long live/record runs.** AFD scenario tests can sit on one pytest item while Azure resources are being created or updated, sometimes for many minutes. Do not assume a hang solely from no new stdout or unchanged recording/XML files, and do not kill a run just because it has been quiet for 5-10 minutes. If xdist output stays quiet after a likely failure point, inspect the env-config result file before deciding next steps:
   ```powershell
   $path = "$env:USERPROFILE\.azdev\env_config\Users\<user>\source\repos\Toolings\azdev\test_results.xml"
   Select-String -Path $path -Pattern 'failure|error|<test_name>' | Select-Object -Last 40
   ```
   The result XML can be written while the terminal still has no final pytest footer. Only stop a run when the user asks, the process exits, there is a clear interactive/error state, the result XML already confirms completion, or there is strong evidence of a real deadlock after checking process health.
6. **Remember that `ScenarioTest.cmd` formats command strings.** `azure-cli-testsdk` calls `command.format(**kwargs)` before execution, so literal raw JSON braces in command strings must be protected. Prefer a mixin/helper that escapes literal `{` and `}` before calling `super().cmd(...)`, or double braces in f-strings where interpolation is needed.
7. **Use generated AAZ argument shape, not REST payload shape.** For generated AAZ commands, raw JSON must match the generated CLI arg schema:
   - Parent list args like `afd rule create --actions/--conditions` may require discriminated wrapper keys such as `[{"route-configuration-override":{"parameters":{...}}}]` or `[{"remote-address":{"parameters":{...}}}]`, not REST shape `[{"name":"RouteConfigurationOverride","parameters":{...}}]`.
   - JSON property names usually follow CLI option spelling (`cache-configuration`, `match-values`, `query-string-caching-behavior`) rather than REST camelCase.
   - Generated property subcommands may expose a different surface from old custom helpers, such as `afd rule action remove --action-name` and `afd rule condition remove --condition-name` instead of `--index`.
   Inspect the generated `_create.py`, `_add.py`, `_remove.py`, or command model before changing tests.
8. **When fixing custom AAZ wrappers, snapshot AAZ objects carefully.** Do not use `copy.deepcopy` on AAZ field/type objects from `ctx.vars.instance`; it can recurse through AAZ dynamic field lookup. For merge/compatibility behavior, snapshot `to_serialized_data()` values or a narrow set of fields, then write those values back in `post_instance_update` or the final pre-request hook.

## Subagent Prompt Template

Use this structure when launching the `Explore` subagent:

```text
Read-only analysis for Azure CLI extension tests.

Context:
- Extension: <cdn|front-door>
- API upgrade: <old-version> -> <new-version>
- Swagger diff summary or file path: <paste summary or point to output>
- Generated CLI/code changes: <paths or git diff scope>

Tasks:
1. Map swagger diff operations/models/properties/enums to CLI commands and arguments.
2. Inspect existing tests and mixins under the relevant extension.
3. Recommend whether to update existing test files or create a new file.
4. Propose concrete test method names, setup steps, CLI commands/options, and assertions.
5. Identify any mixin helper additions.
6. Recommend exact azdev test target(s) for later manual approval.

Do not edit files and do not run tests. Return concise, actionable bullets with file paths.
```

## Test Run Rule

Never run `azdev test`, `pytest`, live tests, or recording generation automatically. Always ask the user first with the exact command(s). If the user declines or does not answer, leave tests unrun and report the proposed command(s).

## References

| File | Contents |
|------|----------|
| [test-generation.md](./references/test-generation.md) | How to map swagger diffs and generated CLI changes to existing or new tests |