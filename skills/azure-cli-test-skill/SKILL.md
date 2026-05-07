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

1. **Gather inputs.** Identify extension (`cdn` or `front-door`), old API version, new API version, the swagger diff output or command/resource area, and any generated CLI files already changed.
2. **Run or read swagger diff.** If no diff is available, run the existing swagger diff helper from `azure-cli-skill` before deciding test coverage:
   ```powershell
   python .github\skills\azure-cli-skill\scripts\swagger_diff.py --ext <cdn|front-door> --old <old-version> --new <new-version>
   ```
3. **Launch a sub agent before editing.** Use `runSubagent` with `agentName: "Explore"` in read-only mode. The subagent must analyze the swagger diff, generated command changes, existing test files, and mixins. It must return:
   - changed operations/models/properties/enums that need test coverage
   - impacted CLI commands and arguments
   - existing test file(s) to update, or why a new file is needed
   - mixin helper changes needed, if any
   - proposed test method names and scenario steps
   - exact test command(s) that could be run later, but do not run them
4. **Map diff to tests.** Use [test-generation.md](./references/test-generation.md) to decide whether to upgrade an existing test file or add a new file.
5. **Edit tests.** Keep changes focused on behavior introduced or changed by the swagger/API update. Prefer existing helpers and scenario style.
6. **Validate without running scenario tests.** Syntax-check edited Python and use diagnostics/lint-style checks when cheap. Do not run `azdev test` yet.
7. **Ask before running tests.** Use `vscode_askQuestions` and show the exact command(s), for example `azdev test test_afd_rule_scenarios::CdnAfdRuleScenarioTest::test_rule_set_batch_mode`. Only run tests after the user explicitly approves. If live mode or recording generation is needed, ask separately.

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