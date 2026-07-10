---
name: azure-cli-test-skill
description: "Generate or update Azure CLI extension scenario tests after swagger/API/AAZ CLI changes. Use for az cdn, az afd, and az network front-door test work, especially when a saved swagger diff must be read and mapped to broad test coverage by updating existing tests or creating new tests. Always starts with a subagent analysis and never runs tests without explicit user approval."
argument-hint: "Describe the API/version and test need, e.g. 'generate cdn 2025-12-01 tests' or 'update afd rule-set tests from swagger diff'"
---

# Azure CLI Test Generation

## Scope

Use this skill to create or update scenario tests for Azure edge CLI extensions:

- `extension/src/cdn/azext_cdn/tests/latest/` — `az cdn ...` and `az afd ...`
- `extension/src/front-door/azext_front_door/tests/latest/test_waf_scenarios.py` — maintained `az network front-door waf-policy ...` tests only

This skill is intentionally separate from swagger/AAZ generation. Swagger upgrade work may hand off here after CLI code is generated.

## Diff Coverage Contract

For swagger/API updates, treat the saved `swagger-diffs/<ext>/<old-version>_to_<new-version>.md` file as the primary coverage source. The goal is to cover as much of the swagger diff as practical through new or updated tests, not merely to add one smoke test.

For generated CLI subcommands, especially AAZ property/subresource commands carved from nested properties, the saved swagger diff may only show the parent resource/model property and not a standalone operation. In that case, treat the generated command surface as an additional coverage source: inspect the generated AAZ command files, command model markdown, and any `azure-cli-aaz-property-subcommands` handoff notes, then add those subcommands to the same coverage matrix.

Before editing tests, build a coverage matrix that maps every relevant diff item to one of these outcomes:

- `update existing test` — extend a nearby scenario or helper to assert the changed CLI behavior.
- `new test` — create a focused test when no existing scenario naturally owns the behavior.
- `covered by existing test` — cite the existing test and assertion that already exercises the diff item.
- `not testable / skip` — give a concrete reason, such as no generated CLI surface, service-side only response noise, operation intentionally unsupported, live-only prerequisite unavailable, or duplicate coverage through a parent operation.

Do not leave updated APIs, new APIs, removed APIs, model/property changes, enum changes, breaking changes, or generated subcommands unmapped. If many model/property changes are only reachable through the same command or subcommand flow, group them under that flow and assert the meaningful persisted fields.

## Required Workflow

1. **Gather inputs.** Identify extension (`cdn` or `front-door`), old API version, new API version, the saved swagger diff path, any generated CLI files already changed, and any new or refreshed CLI subcommands. If the task is a property/subresource command generated from a nested property, identify the parent resource, nested property path, generated command group, and generated command files. If the task is a non-swagger custom-layer cleanup, identify the removed custom command overrides and the generated AAZ commands/arguments that now own the behavior.
2. **Run or read swagger diff when applicable.** If this is a swagger/API update and no saved diff is available, load and follow the `azure-edge-swagger-diff` skill before deciding test coverage. Use the saved `swagger-diffs/<ext>/<old-version>_to_<new-version>.md` file as the required handoff artifact for subagent analysis. Read the file before launching the subagent so the prompt can include the exact path and the high-level diff counts.
   For non-swagger custom-layer cleanup, do not manufacture a swagger diff. Instead, inspect the code diff, generated AAZ schemas, command registrations, existing test commands, and mixin helpers. Treat generated AAZ schemas and generated command examples as authoritative; do not assume a removed flattened option has a one-for-one replacement unless the generated command actually exposes it.
3. **Launch a sub agent before editing.** Use `runSubagent` with `agentName: "Explore"` in read-only mode. The subagent must analyze the swagger diff or non-swagger code diff, generated command changes, existing test files, and mixins. It must return:
   - a coverage matrix for all relevant swagger diff items and generated subcommands, including updated APIs, new APIs, removed APIs, modified models/properties, enum changes, breaking changes, and property/subresource command surfaces
   - impacted CLI commands, subcommands, and arguments
   - existing test file(s) to update, new test file(s) to create, and any diff items already covered
   - diff items that should not be tested, each with a concrete reason
   - mixin helper changes needed, if any
   - proposed test method names and scenario steps
   - exact test command(s) that could be run later, but do not run them
4. **Map diff to tests.** Use [test-generation.md](./references/test-generation.md) to decide whether to upgrade an existing test file or add a new file. Prefer updating existing tests for changed arguments/properties on existing command groups, and create new tests for new command groups or independent setup flows. For custom-layer cleanup, prefer updating existing mixin helpers so scenario intent remains stable while actual CLI invocations use generated AAZ object/list JSON arguments.
5. **Edit tests.** Keep changes focused on behavior introduced or changed by the swagger/API update or custom-layer cleanup. Prefer existing helpers and scenario style. After editing, revisit the coverage matrix and ensure each actionable diff item is covered by a test change or has a skip reason.
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
5. **Expect quiet, long live/record runs.** AFD scenario tests can sit on one pytest item while Azure resources are being created or updated, sometimes for many minutes. Do not assume a hang solely from no new stdout, low CPU, unchanged recording files, or unchanged XML files. Do not actively kill a running UT/live recording because it is quiet or long-running; only stop it when the user explicitly asks, it exits, or it is blocked on a concrete non-secret prompt/process state that cannot complete. If xdist output stays quiet after a likely failure point, inspect the env-config result file before deciding next steps:
   ```powershell
   $path = "$env:USERPROFILE\.azdev\env_config\Users\<user>\source\repos\Toolings\azdev\test_results.xml"
   Select-String -Path $path -Pattern 'failure|error|<test_name>' | Select-Object -Last 40
   ```
   The result XML can be written while the terminal still has no final pytest footer. Report status from terminal output, process state, result XML, and recording timestamps, then keep waiting unless one of the stop conditions above applies.
6. **Update AFD analytic playback time after live recording.** `test_afd_log_analytic` and `test_afd_waf_log_analytic` in `extension/src/cdn/azext_cdn/tests/latest/test_afd_log_analytic_scenarios.py` hard-code `start_time` for playback. After running a live/record test that rewrites `recordings/test_afd_log_analytic.yaml` or `recordings/test_afd_waf_log_analytic.yaml`, inspect the recorded `date-time-begin` value and update the matching playback `datetime.datetime(...)` in the UT to the recorded timestamp so playback requests match the cassette.
7. **Do not commit failed or orphan recordings.** A live run can rewrite a cassette even when the test later fails. Before committing recordings, scan changed cassettes for failure payloads such as `Conflict`, `That resource name isn't available`, `CannotOverwriteExistingCassetteException`, or service-side validation errors; restore failed cassettes instead of committing them. If a stale recording has no current test source or azdev selector, treat it as orphaned and remove it rather than trying to force a recording run. For example, edge-action cassettes can exist without `latest` test selectors.
8. **Respect test decorators and hard-coded resource prerequisites.** `@record_only` tests are skipped by `azdev test --live` until the decorator is intentionally removed. CDN custom-domain BYOC/MSFT tests can be blocked by hard-coded endpoint names required for CNAME validation; if the service returns `That resource name isn't available`, do not commit that failed recording and note the external cleanup requirement.
9. **Remember that `ScenarioTest.cmd` formats command strings.** `azure-cli-testsdk` calls `command.format(**kwargs)` before execution, so literal raw JSON braces in command strings must be protected. Prefer a mixin/helper that escapes literal `{` and `}` before calling `super().cmd(...)`, or double braces in f-strings where interpolation is needed.
10. **Use generated AAZ argument shape, not REST payload shape.** For generated AAZ commands, raw JSON must match the generated CLI arg schema:
   - Parent list args like `afd rule create --actions/--conditions` may require discriminated wrapper keys such as `[{"route-configuration-override":{"parameters":{...}}}]` or `[{"remote-address":{"parameters":{...}}}]`, not REST shape `[{"name":"RouteConfigurationOverride","parameters":{...}}]`.
   - JSON property names usually follow CLI option spelling (`cache-configuration`, `match-values`, `query-string-caching-behavior`) rather than REST camelCase.
   - Generated property subcommands may expose a different surface from old custom helpers, such as `afd rule action remove --action-name` and `afd rule condition remove --condition-name` instead of `--index`.
   Inspect the generated `_create.py`, `_add.py`, `_remove.py`, or command model before changing tests.
11. **When fixing custom AAZ wrappers, snapshot AAZ objects carefully.** Do not use `copy.deepcopy` on AAZ field/type objects from `ctx.vars.instance`; it can recurse through AAZ dynamic field lookup. For merge/compatibility behavior, snapshot `to_serialized_data()` values or a narrow set of fields, then write those values back in `post_instance_update` or the final pre-request hook.

## Subagent Prompt Template

Use this structure when launching the `Explore` subagent:

```text
Read-only analysis for Azure CLI extension tests.

Context:
- Extension: <cdn|front-door>
- API upgrade: <old-version> -> <new-version>
- Saved swagger diff path: swagger-diffs/<ext>/<old-version>_to_<new-version>.md
- Swagger diff summary/counts: <updated APIs, new APIs, removed APIs, model/property changes, enum changes, breaking changes>
- Generated CLI/code changes: <paths or git diff scope>
- Generated subcommands, if any: <command group, verbs, parent resource/property path, generated files>

Tasks:
1. Read the saved swagger diff and map every relevant operation/model/property/enum/breaking-change item to CLI commands and arguments.
2. Inspect generated subcommands, including property/subresource command groups that may not appear as standalone swagger operations.
3. Inspect existing tests and mixins under the relevant extension.
4. Return a coverage matrix with one row per diff item, generated subcommand, or tightly related diff group: diff item/subcommand, CLI surface, test action (`update existing`, `new test`, `already covered`, or `skip`), target file, and reason/assertion.
5. Recommend whether to update existing test files or create a new file.
6. Propose concrete test method names, setup steps, CLI commands/options, and assertions.
7. Identify any mixin helper additions.
8. Recommend exact azdev test target(s) for later manual approval.

Do not edit files and do not run tests. Return concise, actionable bullets with file paths.
```

## Test Run Rule

Never run `azdev test`, `pytest`, live tests, or recording generation automatically. Always ask the user first with the exact command(s). If the user declines or does not answer, leave tests unrun and report the proposed command(s).

## References

| File | Contents |
|------|----------|
| [test-generation.md](./references/test-generation.md) | How to map swagger diffs and generated CLI changes to existing or new tests |