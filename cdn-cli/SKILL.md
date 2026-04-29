---
name: cdn-cli
description: "Develop and maintain Azure edge-related CLI extensions in the azure-cli-extensions repo. Use when working on src/cdn for az cdn or az afd commands, or on src/front-door for az network front-door commands; adding or modifying commands, generating or updating AAZ code, writing scenario tests, debugging command behavior, or changing custom domains, endpoints, origins, profiles, routes, rules, secrets, security policies, WAF policies, or migration flows."
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

## Quick Reference — Swagger Upgrade

When user asks to upgrade a swagger version, follow the workflow in [aaz-dev-setup.md](references/aaz-dev-setup.md) → **Swagger Upgrade Workflow**. Summary:

1. **Prepare Toolings workspace** — use `C:\Users\<User>\source\repos\Toolings` as the workspace and link `.github` to `C:\Users\<User>\source\repos\Skills` (Copilot or manual)
2. **Initialize environment** — run `.github\cdn-cli\scripts\initialize_aaz_dev_env.ps1`; it auto-detects the repo root from the current workspace and creates any missing repo (`extension`, `swagger`, `aaz`, `cli`) plus the `azdev` venv (Copilot)
3. **Activate environment** — run `.github\cdn-cli\scripts\use_aaz_dev_env.ps1` in every new terminal before Python or `aaz-dev` commands (Copilot or manual)
4. **Create branches** — `git checkout -b <branch>` in both `extension` and `aaz` repos (Copilot)
5. **Diff swagger** — run `python .github\cdn-cli\scripts\swagger_diff.py --ext <cdn|front-door> --old <old-ver> --new <new-ver>` to compare versions (Copilot). See [swagger-diff.md](references/swagger-diff.md)
6. **Create workspace** — run `.github\cdn-cli\scripts\auto_select_resources.py --ext <cdn|front-door> --version <ver>` (Copilot). After resources/examples are ready, the script asks whether to Export AAZ and Generate CLI automatically. Use `--auto-export` to answer yes non-interactively, or `--no-auto-export` to review/export manually.
7. **Export + Generate CLI** — If the user answers yes (or `--auto-export` is used), `auto_select_resources.py` exports the workspace to `aaz` and generates extension CLI code. If the user answers no, export manually in Web UI, then run `python .github\cdn-cli\scripts\generate_cli.py --ext <cdn|front-door> --version <ver>`. After generation, the script asks whether to run tests and linter; use `--run-checks` for non-interactive yes or `--no-run-checks` to skip.
8. **Review & test** — `git diff`, bump version, `azdev linter`, `azdev test` (Copilot or manual)

## Agent Workflow Requirements

These are required agent behaviors, even if the helper scripts are not used:

- After adding resources to an AAZ workspace, ask the user whether to automatically **Export AAZ and Generate CLI**. If yes, export the workspace before generating CLI. If no, stop at workspace review and wait for manual Export confirmation.
- After generating CLI code, ask the user whether to run the relevant tests and linter. If yes, run `azdev test test_waf_scenarios` + `azdev linter front-door` for `front-door`, or `azdev test cdn` + `azdev linter cdn` for `cdn`.
- When using non-interactive scripts, prefer `--auto-export` to automatically export/generate and `--run-checks` to automatically run tests/linter. Use `--no-auto-export` and `--no-run-checks` only when the user wants manual review.
- Before Export or CLI generation, ensure generated command/group short summaries are filled and misleading update examples such as `Creates ...` are corrected to `Updates ...`.
