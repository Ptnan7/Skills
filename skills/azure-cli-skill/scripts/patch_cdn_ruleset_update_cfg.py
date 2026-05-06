#!/usr/bin/env python3
"""
Patch the local aaz-dev workspace cfg for the CDN rule-set update generator issue.

This updates only the local .aaz_dev workspace cache. It does not edit the aaz
repo, the extension repo, or swagger files.
"""

import argparse
import base64
import copy
import json
from pathlib import Path


RESOURCE_ID = "/subscriptions/{}/resourcegroups/{}/providers/microsoft.cdn/profiles/{}/rulesets/{}"
RULES_ARG = "$resource.properties.rules"
RULE_NAME_ARG = "$resource.properties.rules[].ruleName"


def encoded_resource_id():
    return base64.urlsafe_b64encode(RESOURCE_ID.encode()).decode()


def find_cfg_path(workspace):
    workspace_root = Path.home() / ".aaz_dev" / "workspaces" / workspace
    direct = workspace_root / "Resources" / encoded_resource_id() / "cfg.json"
    if direct.exists():
        return direct

    resources_root = workspace_root / "Resources"
    if not resources_root.exists():
        raise FileNotFoundError(f"Workspace Resources folder not found: {resources_root}")

    matches = []
    for path in resources_root.rglob("cfg.json"):
        text = path.read_text(encoding="utf-8")
        if RESOURCE_ID in text:
            matches.append(path)
    if not matches:
        raise FileNotFoundError(f"Rule-set cfg.json not found under workspace: {workspace}")
    if len(matches) > 1:
        paths = "\n".join(str(path) for path in matches)
        raise RuntimeError(f"Multiple rule-set cfg.json files found:\n{paths}")
    return matches[0]


def walk(node, path="$"):
    if isinstance(node, dict):
        yield path, node
        for key, value in node.items():
            yield from walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk(value, f"{path}[{index}]")


def find_update_command(data):
    for group in data.get("commandGroups", []):
        if group.get("name") != "cdn profile rule-set":
            continue
        for command in group.get("commands", []):
            if command.get("name") == "update":
                return command
    return None


def find_instance_update_rules(command):
    for _, node in walk(command):
        if node.get("name") == "rules" and node.get("arg") == RULES_ARG:
            return node
    return None


def find_source_rule_name(command):
    for path, node in walk(command):
        if node.get("name") == "ruleName" and ".instanceUpdate." not in path:
            return node
    return None


def patch_cfg(data):
    command = find_update_command(data)
    if command is None:
        return ["cdn profile rule-set update command was not found"], False

    rules = find_instance_update_rules(command)
    if rules is None:
        return ["instanceUpdate rules node was not found"], False

    messages = []
    changed = False

    identifiers = rules.get("identifiers")
    if identifiers != ["ruleName"]:
        rules["identifiers"] = ["ruleName"]
        messages.append(f"set rules identifiers to ['ruleName'] (was {identifiers!r})")
        changed = True

    item = rules.setdefault("item", {"type": "object"})
    props = item.setdefault("props", [])
    rule_name = next((prop for prop in props if prop.get("name") == "ruleName"), None)

    if rule_name is None:
        source = find_source_rule_name(command) or {
            "type": "string",
            "name": "ruleName",
            "required": True,
        }
        rule_name = copy.deepcopy(source)
        rule_name.pop("readOnly", None)
        rule_name["arg"] = RULE_NAME_ARG

        insert_index = len(props)
        for index, prop in enumerate(props):
            if prop.get("name") == "order":
                insert_index = index + 1
                break
        props.insert(insert_index, rule_name)
        messages.append("added rules[].ruleName to instanceUpdate item props")
        changed = True
    elif rule_name.get("arg") != RULE_NAME_ARG:
        previous = rule_name.get("arg")
        rule_name["arg"] = RULE_NAME_ARG
        messages.append(f"set rules[].ruleName arg to {RULE_NAME_ARG!r} (was {previous!r})")
        changed = True

    if not changed:
        messages.append("no patch needed; rules[].ruleName is already present")
    return messages, changed


def main():
    parser = argparse.ArgumentParser(
        description="Patch local aaz-dev cfg for CDN rule-set update rules[].ruleName."
    )
    parser.add_argument("--workspace", required=True, help="aaz-dev workspace name")
    parser.add_argument("--dry-run", action="store_true", help="show what would change without writing")
    parser.add_argument("--no-backup", action="store_true", help="do not create cfg.json.bak before writing")
    args = parser.parse_args()

    cfg_path = find_cfg_path(args.workspace)
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    messages, changed = patch_cfg(data)

    print(f"workspace: {args.workspace}")
    print(f"cfg: {cfg_path}")
    for message in messages:
        print(f"- {message}")

    if args.dry_run or not changed:
        if args.dry_run and changed:
            print("dry run: no file written")
        return

    if not args.no_backup:
        backup_path = cfg_path.with_name("cfg.json.bak")
        if not backup_path.exists():
            backup_path.write_text(cfg_path.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"backup: {backup_path}")

    cfg_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print("patched cfg.json")


if __name__ == "__main__":
    main()