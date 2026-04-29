"""
Auto-select swagger resources for aaz-dev workspace.
Creates a workspace with all resources auto-selected for a given extension.
Resources with existing AAZ command models (inheritance) are auto-selected.

Supports two extensions:
  - cdn:        CDN / AFD commands (Microsoft.Cdn)
  - front-door: Front Door classic WAF commands (Microsoft.Network/frontdoor)

Usage:
    python auto_select_resources.py --ext cdn --version VERSION [--dry-run]
    python auto_select_resources.py --ext front-door --version VERSION [--dry-run]

Examples:
    # Create workspace cdn-2025-09-01-preview with all CDN/AFD resources
    python auto_select_resources.py --ext cdn --version 2025-09-01-preview

    # Create workspace front-door-2025-11-01 with all Front Door WAF resources
    python auto_select_resources.py --ext front-door --version 2025-11-01

    # Dry run
    python auto_select_resources.py --ext front-door --version 2025-11-01 --dry-run
"""

import argparse
import sys
from base64 import b64encode

import requests

from generate_cli import export_workspace, fix_update_examples, get_module, maybe_run_checks, put_module, update_versions

BASE_URL = "http://127.0.0.1:5000"
PLANE = "mgmt-plane"

# Extension profiles: mod_names, resource_provider, workspace prefix, excludes
# IMPORTANT: mod_names must match the swagger module name (used by aaz-dev internally),
# NOT the CLI extension name. Otherwise GenerateExamples and other features fail
# with "Module not find" errors.
EXTENSION_PROFILES = {
    "cdn": {
        "mod_names": "cdn",
        "rp_name": "Microsoft.Cdn",
        "ws_prefix": "cdn",
        "exclude_patterns": ["edgeaction"],
    },
    "front-door": {
        "mod_names": "frontdoor",  # Must be swagger module name, not "front-door"
        "rp_name": "Microsoft.Network",
        "ws_prefix": "front-door",
        "exclude_patterns": [],
    },
}


SUMMARY_VERBS = {
    "create": "Create",
    "delete": "Delete",
    "list": "List",
    "show": "Get",
    "update": "Update",
}

SUMMARY_ACRONYMS = {
    "afd": "AFD",
    "cdn": "CDN",
    "cors": "CORS",
    "ddos": "DDoS",
    "dns": "DNS",
    "fqdn": "FQDN",
    "http": "HTTP",
    "https": "HTTPS",
    "id": "ID",
    "ip": "IP",
    "ssl": "SSL",
    "tls": "TLS",
    "url": "URL",
    "waf": "WAF",
}




def b64(s):
    return b64encode(s.encode()).decode()


def get_existing_workspaces():
    """Get set of existing workspace names."""
    r = requests.get(f"{BASE_URL}/AAZ/Editor/Workspaces")
    r.raise_for_status()
    return {ws["name"] for ws in r.json()}


def get_rp_resources(profile):
    """Get all resources from swagger spec for the given extension profile."""
    mod = profile["mod_names"]
    rp = profile["rp_name"]
    r = requests.get(f"{BASE_URL}/Swagger/Specs/{PLANE}/{mod}/ResourceProviders/{rp}")
    r.raise_for_status()
    return r.json()["resources"]


def get_aaz_resource(resource_id):
    """Check if a resource has existing command models in AAZ."""
    encoded = b64(resource_id)
    r = requests.get(f"{BASE_URL}/AAZ/Specs/Resources/{PLANE}/{encoded}")
    if r.status_code == 200:
        return r.json()
    return None


def create_workspace(name, profile):
    """Create a new workspace."""
    payload = {
        "name": name,
        "plane": PLANE,
        "modNames": profile["mod_names"],
        "resourceProvider": profile["rp_name"],
        "source": "OpenAPI",
    }
    r = requests.post(f"{BASE_URL}/AAZ/Editor/Workspaces", json=payload)
    r.raise_for_status()
    return r.json()


def add_resources_to_workspace(ws_name, version, resources, profile):
    """Add swagger resources to workspace via AddSwagger endpoint.

    Groups resources by version and sends one request per version.
    Each resource can optionally have an aaz_version for inheritance.
    """
    mod = profile["mod_names"]
    # Group resources by their chosen version
    by_version = {}
    for r in resources:
        v = r["version"]
        by_version.setdefault(v, []).append(r)

    for ver, res_list in by_version.items():
        payload_resources = []
        for r in res_list:
            entry = {"id": r["id"]}
            # If there's an existing aaz version, set it for inheritance
            if r.get("aaz_version"):
                entry["options"] = {"aaz_version": r["aaz_version"]}
            payload_resources.append(entry)

        payload = {
            "module": mod,
            "version": ver,
            "resources": payload_resources,
        }
        r = requests.post(
            f"{BASE_URL}/AAZ/Editor/Workspaces/{ws_name}/CommandTree/Nodes/aaz/AddSwagger",
            json=payload,
        )
        r.raise_for_status()

    return True


def select_resources(profile, target_version=None):
    """
    Analyze all resources for the given extension, and select the best version.

    Strategy:
    1. Only select resources that have existing AAZ command models (inheritance)
    2. If target_version specified and resource has it -> use target_version
    3. Otherwise use the latest inherited version
    4. New resources without AAZ history are skipped (add manually in Web UI)
    """
    all_resources = get_rp_resources(profile)
    exclude_patterns = profile.get("exclude_patterns", [])
    selected = []
    skipped = []

    for res in all_resources:
        res_id = res["id"]
        available_versions = [v["version"] for v in res["versions"]]

        # Skip excluded resources
        if any(pat in res_id.lower() for pat in exclude_patterns):
            skipped.append({
                "id": res_id,
                "versions": available_versions[-3:] if available_versions else [],
                "has_aaz": False,
                "reason": "excluded",
            })
            continue

        # Check AAZ for existing command models
        aaz_data = get_aaz_resource(res_id)
        aaz_versions = aaz_data.get("versions", []) if aaz_data else []

        chosen_version = None
        inherit_from = None
        reason = ""

        if aaz_versions:
            aaz_latest = aaz_versions[-1]

            if target_version and target_version in available_versions:
                chosen_version = target_version
                inherit_from = aaz_latest
                reason = f"target version (aaz has: {aaz_latest or 'none'})"
            else:
                for v in reversed(available_versions):
                    if v in aaz_versions:
                        chosen_version = v
                        inherit_from = v
                        reason = "inherited from aaz"
                        break
                if not chosen_version and aaz_versions:
                    chosen_version = aaz_latest
                    inherit_from = aaz_latest
                    reason = "aaz latest"


        if chosen_version:
            entry = {
                "id": res_id,
                "version": chosen_version,
                "reason": reason,
            }
            if inherit_from:
                entry["aaz_version"] = inherit_from
            selected.append(entry)
        else:
            skipped.append({
                "id": res_id,
                "versions": available_versions[-3:] if available_versions else [],
                "has_aaz": bool(aaz_versions),
                "aaz_versions": aaz_versions,
            })

    return selected, skipped


def _choose_version(versions, target_version):
    if target_version and target_version in versions:
        return target_version
    return versions[-1] if versions else target_version


def _print_resource_items(items, show_aaz=False):
    if not items:
        print("  None")
        return
    for idx, item in enumerate(items, start=1):
        print(f"  [{idx}] {item['id']}")
        print(f"      versions: {item.get('versions') or []}")
        if show_aaz:
            print(f"      aaz versions: {item.get('aaz_versions') or []}")


def _ask_include_resources(title, candidates, include_mode, target_version, existing=False):
    if not candidates:
        return []
    if include_mode == "all":
        chosen_indexes = set(range(1, len(candidates) + 1))
    elif include_mode == "none":
        chosen_indexes = set()
    elif not sys.stdin.isatty():
        print(f"\nSkipping prompt for {title} because stdin is not interactive.")
        chosen_indexes = set()
    else:
        print(f"\n{title}")
        _print_resource_items(candidates, show_aaz=existing)
        print("Enter indexes to include (comma-separated), 'all', or press Enter for none.")
        answer = input("Include resources? [none]: ").strip().lower()
        if not answer:
            chosen_indexes = set()
        elif answer == "all":
            chosen_indexes = set(range(1, len(candidates) + 1))
        else:
            chosen_indexes = set()
            for part in answer.split(","):
                part = part.strip()
                if not part:
                    continue
                try:
                    idx = int(part)
                except ValueError:
                    print(f"  Ignoring invalid index: {part}")
                    continue
                if 1 <= idx <= len(candidates):
                    chosen_indexes.add(idx)
                else:
                    print(f"  Ignoring out-of-range index: {idx}")

    included = []
    for idx, item in enumerate(candidates, start=1):
        if idx not in chosen_indexes:
            continue
        entry = {
            "id": item["id"],
            "version": _choose_version(item.get("versions") or [], target_version),
            "reason": "manually included existing AAZ resource" if existing else "manually included new resource",
        }
        if existing and item.get("aaz_versions"):
            entry["aaz_version"] = item["aaz_versions"][-1]
        included.append(entry)
    return included


def finalize_selected_resources(selected, skipped, target_version, include_new, include_existing):
    """Print resource lists and optionally add skipped resources to the final AddSwagger list."""
    selected_ids = {item["id"] for item in selected}
    new_candidates = [
        item for item in skipped
        if not item.get("has_aaz") and item["id"] not in selected_ids
    ]
    existing_unselected = [
        item for item in skipped
        if item.get("has_aaz") and item["id"] not in selected_ids
    ]

    print("\n=== RESOURCE PLAN BEFORE AddSwagger ===")
    print(f"\nSelected existing APIs to update/add ({len(selected)}):")
    if selected:
        for item in selected:
            print(f"  - {item['id']}")
            print(f"      version: {item['version']}  ({item['reason']})")
            if item.get("aaz_version"):
                print(f"      inherit from AAZ: {item['aaz_version']}")
    else:
        print("  None")

    print(f"\nNew APIs not in AAZ ({len(new_candidates)}):")
    _print_resource_items(new_candidates)
    print("  Ask whether any of these need to be created as new commands/resources.")

    print(f"\nExisting AAZ APIs not selected ({len(existing_unselected)}):")
    _print_resource_items(existing_unselected, show_aaz=True)
    print("  Ask whether any of these existing APIs still need to be added.")

    additions = []
    additions.extend(_ask_include_resources(
        "New APIs not in AAZ: should any be created?",
        new_candidates,
        include_new,
        target_version,
        existing=False,
    ))
    additions.extend(_ask_include_resources(
        "Existing AAZ APIs not selected: should any still be added?",
        existing_unselected,
        include_existing,
        target_version,
        existing=True,
    ))

    final = [*selected]
    final_ids = {item["id"] for item in final}
    for item in additions:
        if item["id"] not in final_ids:
            final.append(item)
            final_ids.add(item["id"])
    return final, new_candidates, existing_unselected


def print_add_swagger_payload(resources, profile):
    """Print the final AddSwagger payload grouped by version."""
    by_version = {}
    for item in resources:
        by_version.setdefault(item["version"], []).append(item)

    print("\n=== FINAL AddSwagger RESOURCE PARAMETERS ===")
    if not resources:
        print("  None")
        return
    for version, items in by_version.items():
        print(f"\nmodule: {profile['mod_names']}")
        print(f"version: {version}")
        print("resources:")
        for item in items:
            print(f"  - id: {item['id']}")
            if item.get("aaz_version"):
                print(f"    options:")
                print(f"      aaz_version: {item['aaz_version']}")


def _walk_command_tree(node, path_parts=None):
    """Recursively yield (group_path, leaf_name) for API calls.

    group_path is like "network/front-door/waf-policy" (slash-separated).
    leaf_name is the command name like "create", "list".
    """
    if path_parts is None:
        path_parts = []

    if "commands" in node:
        grp_path = "/".join(path_parts)
        for leaf_name in node["commands"]:
            yield grp_path, leaf_name

    if "commandGroups" in node:
        for grp_name, grp in node["commandGroups"].items():
            yield from _walk_command_tree(grp, path_parts + [grp_name])


def _walk_command_groups(node, path_parts=None):
    """Recursively yield (group_path, node) for command groups."""
    if path_parts is None:
        path_parts = []

    if path_parts:
        yield "/".join(path_parts), node

    if "commandGroups" in node:
        for grp_name, grp in node["commandGroups"].items():
            yield from _walk_command_groups(grp, path_parts + [grp_name])


def _format_command_segment(segment):
    words = []
    for word in segment.replace("_", "-").split("-"):
        words.append(SUMMARY_ACRONYMS.get(word.lower(), word.lower()))
    return " ".join(words)


def _pluralize_phrase(phrase):
    words = phrase.split()
    if not words:
        return phrase
    word = words[-1]
    lower = word.lower()
    if lower.endswith("y") and (len(lower) < 2 or lower[-2] not in "aeiou"):
        words[-1] = f"{word[:-1]}ies"
    elif not lower.endswith("s"):
        words[-1] = f"{word}s"
    return " ".join(words)


def _get_resource_phrase(names):
    if len(names) < 2:
        return "resource"
    return _format_command_segment(names[-2])


def _build_command_summary(command):
    names = command.get("names", [])
    leaf_name = names[-1] if names else ""
    verb = SUMMARY_VERBS.get(leaf_name, leaf_name.capitalize() if leaf_name else "Manage")
    resource = _get_resource_phrase(names)
    if leaf_name == "list":
        resource = _pluralize_phrase(resource)
    return f"{verb} {resource}."


def _build_group_summary(group):
    names = group.get("names", [])
    resource = _format_command_segment(names[-1]) if names else "resources"
    return f"Manage {_pluralize_phrase(resource)}."


def fill_missing_short_summaries(ws_name):
    """Patch generated commands/groups that have no help.short."""
    r = requests.get(f"{BASE_URL}/AAZ/Editor/Workspaces/{ws_name}")
    if r.status_code != 200:
        print(f"    Could not load workspace for summaries: {r.status_code}")
        return

    ws_data = r.json()
    tree = ws_data.get("commandTree", {})
    updated_groups = 0
    updated_commands = 0

    for grp_path, group in _walk_command_groups(tree):
        help_data = group.get("help") or {}
        if not help_data.get("short"):
            summary = _build_group_summary(group)
            patch_url = f"{BASE_URL}/AAZ/Editor/Workspaces/{ws_name}/CommandTree/Nodes/aaz/{grp_path}"
            r = requests.patch(patch_url, json={"help": {"short": summary, "lines": help_data.get("lines", [])}})
            if r.status_code == 200:
                print(f"    {grp_path}: {summary}")
                updated_groups += 1
            else:
                print(f"    {grp_path}: summary patch failed ({r.status_code})")

    r = requests.get(f"{BASE_URL}/AAZ/Editor/Workspaces/{ws_name}")
    if r.status_code != 200:
        print(f"    Could not reload workspace for command summaries: {r.status_code}")
        return
    tree = r.json().get("commandTree", {})

    for grp_path, leaf_name in _walk_command_tree(tree):
        leaf_url = f"{BASE_URL}/AAZ/Editor/Workspaces/{ws_name}/CommandTree/Nodes/aaz/{grp_path}/Leaves/{leaf_name}"
        r = requests.get(leaf_url)
        if r.status_code != 200:
            print(f"    {grp_path}/{leaf_name}: load failed ({r.status_code})")
            continue
        command = r.json()
        help_data = command.get("help") or {}
        if help_data.get("short"):
            continue
        summary = _build_command_summary(command)
        r = requests.patch(leaf_url, json={"help": {"short": summary, "lines": help_data.get("lines", [])}})
        if r.status_code == 200:
            print(f"    {grp_path}/{leaf_name}: {summary}")
            updated_commands += 1
        else:
            print(f"    {grp_path}/{leaf_name}: summary patch failed ({r.status_code})")

    print(f"  Short summaries: {updated_groups} group(s), {updated_commands} command(s) updated")


def generate_examples_for_workspace(ws_name):
    """Call GenerateExamples(source=swagger) + patch for every command in workspace.

    This loads x-ms-examples from the swagger spec into the workspace commands.
    Requires the CLI extension to be installed (pip install -e) and aaz-dev
    running from the azdev venv.

    Also fixes common swagger example issues:
    - CreateOrUpdate operations share one example across 'create' and 'update'
      commands, so 'update' commands may inherit a "Creates ..." example name.
      The script rewrites these to "Updates ..." automatically.
    """
    r = requests.get(f"{BASE_URL}/AAZ/Editor/Workspaces/{ws_name}")
    if r.status_code != 200:
        print(f"    Could not load workspace: {r.status_code}")
        return

    ws_data = r.json()
    tree = ws_data.get("commandTree", {})

    count = 0
    errors = 0
    for grp_path, leaf_name in _walk_command_tree(tree):
        gen_url = (
            f"{BASE_URL}/AAZ/Editor/Workspaces/{ws_name}"
            f"/CommandTree/Nodes/aaz/{grp_path}/Leaves/{leaf_name}/GenerateExamples"
        )
        r = requests.post(gen_url, json={"source": "swagger"})
        if r.status_code == 200:
            examples = r.json()
            if examples:
                # Fix misleading example names for update commands.
                # Swagger CreateOrUpdate operations produce one example that is
                # shared by both the 'create' and 'update' AAZ commands.  The
                # example name often starts with "Create" which is wrong for
                # the update command.
                if leaf_name == "update":
                    for ex in examples:
                        name = ex.get("name", "")
                        if name.lower().startswith("create"):
                            fixed = "Update" + name[len("Create"):]
                            ex["name"] = fixed

                # Patch examples into the command
                patch_url = (
                    f"{BASE_URL}/AAZ/Editor/Workspaces/{ws_name}"
                    f"/CommandTree/Nodes/aaz/{grp_path}/Leaves/{leaf_name}/Examples"
                )
                r2 = requests.patch(patch_url, json={"examples": examples})
                if r2.status_code == 200:
                    ex_names = [e.get("name", "") for e in examples]
                    print(f"    {grp_path}/{leaf_name}: {ex_names}")
                    count += 1
                else:
                    print(f"    {grp_path}/{leaf_name}: patch failed ({r2.status_code})")
                    errors += 1
        else:
            # 404 = module not installed, 400 = no operations
            errors += 1

    print(f"  Examples: {count} commands updated, {errors} skipped/failed")
    if errors > 0:
        print("  (Ensure extension is installed: pip install -e src/<ext>)")


def ask_export_and_generate(auto_export, no_auto_export):
    """Return whether to export workspace and generate CLI after resource setup."""
    if auto_export and no_auto_export:
        raise ValueError("--auto-export and --no-auto-export cannot be used together")
    if auto_export:
        return True
    if no_auto_export:
        return False
    if not sys.stdin.isatty():
        print("\nSkipping Export/Generate prompt because stdin is not interactive.")
        print("Use --auto-export to export AAZ and generate CLI automatically.")
        return False

    while True:
        answer = input("\nExport workspace to AAZ and generate CLI now? [y/N]: ").strip().lower()
        if answer in ("", "n", "no"):
            return False
        if answer in ("y", "yes"):
            return True
        print("Please answer y or n.")


def export_and_generate_cli(ext, version, ws_name):
    """Export workspace to AAZ, then generate CLI code for the extension."""
    print(f"\nExporting workspace '{ws_name}' to AAZ...")
    if not export_workspace(ws_name):
        return False

    print(f"Generating CLI module: {ext}")
    data = get_module(ext)
    profiles = data.get("profiles") or {}
    latest = profiles.get("latest")
    if not latest:
        print("ERROR: module has no 'profiles.latest' node; Export may have failed.", file=sys.stderr)
        return False

    counts = {"commands_total": 0, "commands_changed": 0, "wait_changed": 0}
    update_versions(latest, version, counts)
    print(f"Commands in module: {counts['commands_total']}")
    print(f"  version changes:  {counts['commands_changed']}")
    print(f"  waitCommand changes: {counts['wait_changed']}")
    print(f"  target version:   {version}")

    print(f"PUT {BASE_URL}/CLI/Az/Extension/Modules/{ext} (triggers code generation)...")
    put_module(ext, data)
    fix_update_examples(ext)
    print("Done. Review changes with: git -C $env:AAZ_CLI_EXTENSION_PATH status")
    return True


def maybe_export_and_generate_cli(args, ws_name):
    try:
        should_export = ask_export_and_generate(args.auto_export, args.no_auto_export)
    except ValueError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    if should_export:
        if not export_and_generate_cli(args.ext, args.version, ws_name):
            sys.exit(1)
        maybe_run_checks(args.ext, args.run_checks, args.no_run_checks)
    else:
        print(f"\nOpen http://127.0.0.1:5000 to review workspace '{ws_name}'.")
        print("When ready, export manually or rerun with --auto-export.")


def main():
    parser = argparse.ArgumentParser(description="Auto-select swagger resources for aaz-dev workspace")
    parser.add_argument("--ext", "-e", required=True, choices=EXTENSION_PROFILES.keys(),
                        help="Extension to target (cdn or front-door)")
    parser.add_argument("--version", "-v", required=True, help="Target API version (e.g. 2025-11-01)")
    parser.add_argument("--workspace", "-w", help="Custom workspace name (default: <ext>-<version>)")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would be selected")
    parser.add_argument("--auto-export", action="store_true",
                        help="After resource setup, export the workspace to AAZ and generate CLI without prompting")
    parser.add_argument("--no-auto-export", action="store_true",
                        help="After resource setup, skip the Export/Generate prompt")
    parser.add_argument("--run-checks", action="store_true",
                        help="After auto Export/Generate, run the relevant azdev test target and linter without prompting")
    parser.add_argument("--no-run-checks", action="store_true",
                        help="After auto Export/Generate, skip the test/linter prompt")
    parser.add_argument("--include-new-resources", choices=("all", "none"), default=None,
                        help="Whether to include new resources that have no AAZ history without prompting")
    parser.add_argument("--include-existing-skipped", choices=("all", "none"), default=None,
                        help="Whether to include skipped resources that already have AAZ history without prompting")
    args = parser.parse_args()

    profile = EXTENSION_PROFILES[args.ext]
    ws_name = args.workspace or f"{profile['ws_prefix']}-{args.version}"

    print(f"Analyzing {args.ext} resources for version {args.version}...")
    print(f"  Extension:  {args.ext}")
    print(f"  Module:     {profile['mod_names']}")
    print(f"  RP:         {profile['rp_name']}")
    print(f"  Workspace:  {ws_name}")

    selected, skipped = select_resources(profile, target_version=args.version)

    print(f"\n=== SELECTED: {len(selected)} resources ===")
    for r in selected:
        print(f"  [+] {r['id']}")
        print(f"      version: {r['version']}  ({r['reason']})")

    print(f"\n=== SKIPPED: {len(skipped)} resources ===")
    for r in skipped:
        print(f"  [-] {r['id']}")
        print(f"      versions: {r['versions']}  aaz: {r['has_aaz']}")

    selected, _, _ = finalize_selected_resources(
        selected,
        skipped,
        args.version,
        "none" if args.dry_run else args.include_new_resources,
        "none" if args.dry_run else args.include_existing_skipped,
    )
    print_add_swagger_payload(selected, profile)

    if args.dry_run:
        print("\n(dry run - no changes made)")
        return

    if not selected:
        print("\nNo resources to add.")
        return

    existing = get_existing_workspaces()
    if ws_name in existing:
        print(f"\nWorkspace '{ws_name}' already exists, skipping.")
        print(f"  Filling missing short summaries in existing workspace...")
        fill_missing_short_summaries(ws_name)
        print(f"  Refreshing/fixing generated examples in existing workspace...")
        generate_examples_for_workspace(ws_name)
        maybe_export_and_generate_cli(args, ws_name)
        return

    print(f"\nCreating workspace '{ws_name}'...")
    ws = create_workspace(ws_name, profile)
    print(f"  Created: {ws['url']}")

    print(f"  Adding {len(selected)} resources...")
    try:
        add_resources_to_workspace(ws_name, args.version, selected, profile)
        print(f"  Done!")
    except requests.exceptions.HTTPError as e:
        print(f"  Error: {e.response.status_code} - {e.response.text[:500]}")

    print(f"\n  Filling missing short summaries...")
    fill_missing_short_summaries(ws_name)

    # Generate examples from swagger x-ms-examples for each command
    print(f"\n  Generating examples from swagger...")
    generate_examples_for_workspace(ws_name)

    maybe_export_and_generate_cli(args, ws_name)


if __name__ == "__main__":
    main()
