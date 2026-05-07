---
name: azure-cli-skill
description: "Develop and maintain Azure edge-related CLI extensions in the azure-cli-extensions repo. Use for az cdn and az afd work in src/cdn, and az network front-door classic work in src/front-door; upgrading swagger, API, or CLI command versions consumed by those CLI extensions; adding or modifying commands, generating or updating AAZ code, writing scenario tests, debugging command behavior, or changing custom domains, endpoints, origins, profiles, routes, rules, secrets, security policies, WAF policies, or migration flows. Do NOT use for authoring or reviewing OpenAPI/TypeSpec specs in the swagger repo unless the task is specifically about consuming those specs to regenerate CLI."
argument-hint: "Describe the extension task, e.g. 'add afd route support in src/cdn' or 'fix network front-door waf policy in src/front-door'"
---

# Azure Edge CLI Extension Development

## Overview

This skill covers two extensions in the `azure-cli-extensions` repo:

- `src/cdn/azext_cdn/` — **Azure CDN** (`az cdn ...`) and **Azure Front Door Standard/Premium** (`az afd ...`), fully AAZ-driven
- `src/front-door/azext_front_door/` — **Azure Front Door classic** (`az network front-door ...`), legacy; only the `aaz/latest/network/front_door/` subtree is actively maintained

## Reference Files

| File | Contents |
|------|----------|
| [workflow-diagram.md](references/workflow-diagram.md) | Mermaid flowchart of the full swagger-upgrade workflow |
| [architecture.md](references/architecture.md) | Project structure, command groups, SDK dependencies |
| [aaz-dev-setup.md](references/aaz-dev-setup.md) | Local environment, code generation, auto-select script, **swagger upgrade workflow** |
| [swagger-diff.md](references/swagger-diff.md) | Compare old vs new swagger (local or GitHub) before updating AAZ code |
| [development.md](references/development.md) | Adding commands, AAZ patterns, registration, lint, pitfalls |
| [testing.md](references/testing.md) | Test structure, running tests, writing tests |

## Issue Runbooks

| Issue | Use When |
|-------|----------|
| [aaz-export-before-cli-generation.md](issues/aaz-export-before-cli-generation.md) | CLI generation loses examples or generated output lacks examples because the workspace was not exported first. |
| [generated-update-example-says-create.md](issues/generated-update-example-says-create.md) | Generated `update` command examples/docstrings say `Create` or `Creates`. |
| [azdev-test-missing-setup.md](issues/azdev-test-missing-setup.md) | `azdev test` fails with `Unable to retrieve CLI repo path from config`. |
| [front-door-legacy-files-tests.md](issues/front-door-legacy-files-tests.md) | Front Door work touches legacy files or legacy non-WAF tests fail. |
| [cdn-ruleset-update-drops-rule-name.md](issues/cdn-ruleset-update-drops-rule-name.md) | aaz-dev drops `rules[].ruleName` from `cdn profile rule-set update` `instanceUpdate` cfg. |
| [cdn-missing-target-command-model.md](issues/cdn-missing-target-command-model.md) | CDN generation fails because a command lacks a target API AAZ command model and must stay on its old API. |

## Quick Reference — Swagger Upgrade

When user asks to upgrade a swagger version, follow the workflow in [aaz-dev-setup.md](references/aaz-dev-setup.md) → **Swagger Upgrade Workflow**. Summary:

1. **Prepare Toolings workspace** — use `C:\Users\<User>\source\repos\Toolings` as the workspace and link `.github` to `C:\Users\<User>\source\repos\Skills` (Copilot or manual)
2. **Initialize environment** — run `.github\skills\azure-cli-skill\scripts\initialize_aaz_dev_env.ps1`; it auto-detects the repo root from the current workspace and creates any missing repo (`extension`, `swagger`, `aaz`, `cli`) plus the `azdev` venv (Copilot)
3. **Activate environment** — run `.github\skills\azure-cli-skill\scripts\use_aaz_dev_env.ps1` in every new terminal before Python or `aaz-dev` commands (Copilot or manual)
4. **Create branches** — `git checkout -b <branch>` in both `extension` and `aaz` repos (Copilot)
5. **Diff swagger** — run `python .github\skills\azure-cli-skill\scripts\swagger_diff.py --ext <cdn|front-door> --old <old-ver> --new <new-ver>` to compare versions (Copilot). After the diff, provide a detailed list of updated APIs, new APIs, and AddSwagger resource candidates. See [swagger-diff.md](references/swagger-diff.md)
6. **Create workspace** — run `.github\skills\azure-cli-skill\scripts\auto_select_resources.py --ext <cdn|front-door> --version <ver>` (Copilot). Before AddSwagger, show the selected resources, new APIs not in AAZ, existing AAZ APIs not selected, and the final AddSwagger resource parameters. Ask whether any new APIs should be created and whether any existing-but-unselected APIs should be added. For CDN rule-set batch mode updates, apply [cdn-ruleset-update-drops-rule-name.md](issues/cdn-ruleset-update-drops-rule-name.md) before Export if aaz-dev drops `rules[].ruleName` from the update `instanceUpdate` schema. After resources/examples are ready, the script asks whether to Export AAZ and Generate CLI automatically. Use `--auto-export` to answer yes non-interactively, or `--no-auto-export` to review/export manually.
7. **Export + Generate CLI** — If the user answers yes (or `--auto-export` is used), `auto_select_resources.py` exports the workspace to `aaz` and generates extension CLI code. For `cdn`, first apply [cdn-missing-target-command-model.md](issues/cdn-missing-target-command-model.md): keep commands without target AAZ command models on their existing API instead of blindly bumping every command. If the user answers no, export manually in Web UI, then run `python .github\skills\azure-cli-skill\scripts\generate_cli.py --ext <cdn|front-door> --version <ver>`. After generation, ask whether to run linter; use `--run-linter` for non-interactive yes or `--no-run-linter` to skip.
8. **Ask to run linter only** — Do not require a generated diff review gate. Ask only whether to run `azdev linter <ext>`, then proceed to version/changelog work after linter passes or is intentionally skipped. Do not run `azdev test` from this skill; version-specific test selection belongs in `azure-cli-test-skill`.

## Agent Workflow Requirements

These are required agent behaviors, even if the helper scripts are not used:

- After adding resources to an AAZ workspace, ask the user whether to automatically **Export AAZ and Generate CLI**. If yes, export the workspace before generating CLI. If no, stop at workspace review and wait for manual Export confirmation.
- For CDN rule-set batch mode updates, check [cdn-ruleset-update-drops-rule-name.md](issues/cdn-ruleset-update-drops-rule-name.md) before Export. If the workaround is needed, patch only the local `.aaz_dev` workspace cfg and never hand-edit generated files in the `aaz` repo.
- For `cdn` swagger/API upgrades, do not blindly force every existing command to the target API. Before CLI generation, check [cdn-missing-target-command-model.md](issues/cdn-missing-target-command-model.md) and preserve old APIs for commands that lack a real target AAZ command model.
- After generating CLI code, do not insert a required generated-diff review step. Ask the user only whether to run `azdev linter <ext>`. Do not run `azdev test` from this skill; hand off version-specific test generation or test selection to `azure-cli-test-skill`.
- After swagger diff, summarize resource-level impact: updated APIs, new APIs, and AddSwagger candidates. Before AddSwagger, summarize all resources to be passed as AddSwagger parameters, and explicitly ask whether new APIs should be created and whether existing AAZ APIs that were not selected should still be added.
- When using non-interactive scripts, prefer `--auto-export` to automatically export/generate and `--run-linter` to automatically run linter only. Use `--no-auto-export` and `--no-run-linter` only when the user wants manual review.
- Before Export or CLI generation, ensure generated command/group short summaries are filled and misleading update examples such as `Creates ...` are corrected to `Updates ...`.
- Never stage or commit automatically. After version/changelog work, show `git status --short` in both the `extension` and `aaz` repos, then ask whether to commit.
