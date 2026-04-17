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
            })

    return selected, skipped


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


def generate_examples_for_workspace(ws_name):
    """Call GenerateExamples(source=swagger) + patch for every command in workspace.

    This loads x-ms-examples from the swagger spec into the workspace commands.
    Requires the CLI extension to be installed (pip install -e) and aaz-dev
    running from the azdev venv.
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
                    print(f"    {cmd_path}: patch failed ({r2.status_code})")
                    errors += 1
        else:
            # 404 = module not installed, 400 = no operations
            errors += 1

    print(f"  Examples: {count} commands updated, {errors} skipped/failed")
    if errors > 0:
        print("  (Ensure extension is installed: pip install -e src/<ext>)")


def main():
    parser = argparse.ArgumentParser(description="Auto-select swagger resources for aaz-dev workspace")
    parser.add_argument("--ext", "-e", required=True, choices=EXTENSION_PROFILES.keys(),
                        help="Extension to target (cdn or front-door)")
    parser.add_argument("--version", "-v", required=True, help="Target API version (e.g. 2025-11-01)")
    parser.add_argument("--workspace", "-w", help="Custom workspace name (default: <ext>-<version>)")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would be selected")
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

    if args.dry_run:
        print("\n(dry run - no changes made)")
        return

    if not selected:
        print("\nNo resources to add.")
        return

    existing = get_existing_workspaces()
    if ws_name in existing:
        print(f"\nWorkspace '{ws_name}' already exists, skipping.")
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

    # Generate examples from swagger x-ms-examples for each command
    print(f"\n  Generating examples from swagger...")
    generate_examples_for_workspace(ws_name)

    print(f"\nOpen http://127.0.0.1:5000 to view and edit the workspace.")


if __name__ == "__main__":
    main()
