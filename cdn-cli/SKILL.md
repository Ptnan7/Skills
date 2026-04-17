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
| [architecture.md](references/architecture.md) | Project structure, command groups, SDK dependencies |
| [aaz-dev-setup.md](references/aaz-dev-setup.md) | Local environment, code generation, auto-select script, **swagger upgrade workflow** |
| [swagger-diff.md](references/swagger-diff.md) | Compare old vs new swagger (local or GitHub) before updating AAZ code |
| [development.md](references/development.md) | Adding commands, AAZ patterns, registration, lint, pitfalls |
| [testing.md](references/testing.md) | Test structure, running tests, writing tests |

## Quick Reference — Swagger Upgrade

When user asks to upgrade a swagger version, follow the workflow in [aaz-dev-setup.md](references/aaz-dev-setup.md) → **Swagger Upgrade Workflow**. Summary:

1. **Create branches** — `git checkout -b <branch>` in both `extension` and `aaz` repos (Copilot)
2. **Diff swagger** — compare old vs new (use [swagger-diff.md](references/swagger-diff.md))
3. **Create workspace** — run `auto_select_resources.py --ext <cdn|front-door> --version <ver>` (Copilot)
4. **Export workspace** — **Manual** in Web UI (user clicks Export). Wait for user to confirm.
5. **Generate CLI** — After user confirms Export, agent calls API to update versions and generate code (Copilot)
6. **Review & test** — `git diff`, bump version, `azdev linter`, `azdev test` (Copilot or manual)
