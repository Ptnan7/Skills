# Test Generation Reference

## Inputs To Inspect

Start from evidence, not guesses:

- Swagger diff: modified/new operations, model/property changes, enum changes, breaking changes.
- Generated CLI files: AAZ command files under `extension/src/<ext>/azext_*/aaz/latest/` and AAZ command model markdown under `aaz/Commands/...`.
- Existing tests: closest `test_*_scenarios.py` file and any mixin helper in `scenario_mixin.py`, `afdx_scenario_mixin.py`, or `frontdoor_test_util.py`.
- Existing recordings only as context. Do not regenerate recordings unless the user explicitly approves a live/recording run.

## Update Existing File Or Add New File

Prefer updating an existing test file when:

- The changed command group already has a scenario file, such as `test_afd_rule_scenarios.py` for `az afd rule` / `az afd rule-set`.
- The swagger diff adds an argument/property to an existing create/update/list/show flow.
- The new behavior can be validated by extending an existing CRUD scenario without making it fragile or too long.

Create a new test file when:

- The swagger diff introduces a new command group with no close existing scenario file.
- The scenario requires a distinct resource setup or should not lengthen a large existing scenario.
- The feature is independent enough to run as its own targeted `azdev test test_<feature>_scenarios` command.

## CDN / AFD Test Patterns

Location: `extension/src/cdn/azext_cdn/tests/latest/`

- Use `CdnScenarioMixin` for `az cdn ...` tests.
- Use `CdnAfdScenarioMixin` for `az afd ...` tests.
- Prefer existing mixin helpers when available.
- Add a mixin helper when the command is reused or matches existing helper style.
- Direct `self.cmd(...)` is acceptable for one-off assertions or a command with no useful helper pattern.
- Use `ResourceGroupPreparer(additional_tags={'owner': 'jingnanxu'})` unless a nearby file uses a stricter preparer.
- Prefer `self.create_random_name(...)` for resource names unless the service requires stable DNS/custom-domain names.
- Use `JMESPathCheck` for response shape and property assertions.

Representative files:

- `test_profile_scenarios.py` for CDN profile behavior.
- `test_endpoint_scenarios.py` for CDN endpoint behavior.
- `test_afd_profile_scenarios.py` for AFD profile behavior.
- `test_afd_endpoint_scenarios.py` for AFD endpoint behavior.
- `test_afd_route_scenarios.py` for AFD route behavior.
- `test_afd_rule_scenarios.py` for AFD rule and rule-set behavior.
- `test_afd_security_policy_scenarios.py` for AFD security policy behavior.

## Front Door Test Patterns

Location: `extension/src/front-door/azext_front_door/tests/latest/`

- Maintained generated/custom test work should target `test_waf_scenarios.py` and `frontdoor_test_util.py`.
- Legacy non-WAF tests are not maintained for swagger-upgrade work unless the user explicitly asks.
- Use existing `WafScenarioMixin` patterns and direct `self.cmd(...)` command sequences.

## Coverage Heuristics

For a swagger/API change, cover the smallest meaningful behavior surface:

- New create/update argument: create or update with the argument, then assert the returned JSON property.
- New list/show response property: create/update a resource that has the property, then assert list/show returns it.
- New enum value: use the new enum in a valid command and assert the service returns it.
- New nested list/object property: verify at least one item with stable identifiers and key nested fields.
- Changed operation request body: validate the generated CLI can send the new body shape, then assert persisted fields.
- Error behavior: add an expect-failure or exception assertion only when the swagger change alters validation or a known service error is part of the CLI contract.

Avoid broad CRUD rewrites when one focused test or one extension to an existing scenario is enough.

## Test Run Approval

After edits, propose exact commands but do not run them until approved. Examples:

```powershell
azdev test test_afd_rule_scenarios::CdnAfdRuleScenarioTest::test_rule_set_batch_mode
azdev test test_waf_scenarios::WafTests::test_waf_policy_managed_rules_sensitivity
```

Ask separately for live mode or recording generation:

```powershell
azdev test test_afd_rule_scenarios::CdnAfdRuleScenarioTest::test_rule_set_batch_mode --live
```