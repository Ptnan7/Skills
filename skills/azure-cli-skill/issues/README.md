# Azure Edge CLI Known Issues

Use these runbooks when a CDN/AFD swagger or AAZ generation task hits a known failure mode. These are quick operational notes; longer workflow docs stay under `references/`.

| Issue | When to Use |
|-------|-------------|
| [aaz-export-before-cli-generation.md](aaz-export-before-cli-generation.md) | CLI generation loses examples or generated output lacks examples because the workspace was not exported first. |
| [generated-update-example-says-create.md](generated-update-example-says-create.md) | Generated `update` command examples/docstrings say `Create` or `Creates`. |
| [azdev-test-missing-setup.md](azdev-test-missing-setup.md) | `azdev test` fails with `Unable to retrieve CLI repo path from config`. |
| [front-door-legacy-files-tests.md](front-door-legacy-files-tests.md) | Front Door work touches legacy files or legacy non-WAF tests fail. |
| [cdn-ruleset-update-drops-rule-name.md](cdn-ruleset-update-drops-rule-name.md) | `cdn profile rule-set update` drops `rules[].ruleName` from local `.aaz_dev` `instanceUpdate` cfg before Export. |
| [cdn-missing-target-command-model.md](cdn-missing-target-command-model.md) | CDN CLI generation fails because an existing command has no AAZ command model for the target API version. |
