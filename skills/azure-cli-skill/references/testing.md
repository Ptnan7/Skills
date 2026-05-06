# Testing

## Test Structure

### `src/cdn`

Tests use `ScenarioTest` from `azure.cli.testsdk` with two mixin classes:

- `CdnScenarioMixin` (`tests/latest/scenario_mixin.py`) — helpers for `az cdn` commands
- `CdnAfdScenarioMixin` (`tests/latest/afdx_scenario_mixin.py`) — helpers for `az afd` commands

### `src/front-door`

Only tests covering the AAZ-generated `waf-policy` commands are actively maintained. Legacy tests for backend pools, frontend endpoints, routing rules, probes, and rules engine are not maintained. See [front-door-legacy-files-tests.md](../issues/front-door-legacy-files-tests.md).

---

## Running Tests

```bash
# All CDN/AFD tests
azdev test cdn

# Specific CDN test file
azdev test test_endpoint_scenarios

# Specific CDN test method
azdev test test_endpoint_scenarios::CdnEndpointScenarioTest::test_endpoint_crud

# Live mode (against real Azure, generates recordings)
azdev test cdn --live

# Front Door WAF tests
azdev test front-door

# Specific Front Door test
azdev test test_waf_scenarios

# Live mode
azdev test front-door --live
```

---

## Writing a `src/cdn` Test

```python
from azure.cli.testsdk import ResourceGroupPreparer, JMESPathCheck, ScenarioTest
from .scenario_mixin import CdnScenarioMixin

class CdnMyFeatureTest(CdnScenarioMixin, ScenarioTest):
    @ResourceGroupPreparer(additional_tags={'owner': 'jingnanxu'})
    def test_my_feature(self, resource_group):
        profile_name = 'profile123'
        self.profile_create_cmd(resource_group, profile_name)

        checks = [JMESPathCheck('name', profile_name)]
        self.profile_show_cmd(resource_group, profile_name, checks=checks)
```

Use `CdnScenarioMixin` helpers (`profile_create_cmd`, `endpoint_create_cmd`, `origin_show_cmd`, etc.) rather than calling `self.cmd(...)` directly when helpers already exist.

---

## Notes

- Test recordings live in `tests/latest/recordings/` and can be large. Only regenerate recordings when the scenario actually changes.
- When adding a new command in `src/cdn`, add a corresponding test and run in live mode to capture a fresh recording.
- For `src/front-door`, limit new test work to commands under `azext_front_door/aaz/` (primarily WAF policy). See [front-door-legacy-files-tests.md](../issues/front-door-legacy-files-tests.md).
