"""
Generate CLI extension code via the aaz-dev web UI API.

Covers Step 5 of the swagger-upgrade workflow:
  1. (Optional) Export a workspace -> writes command models + examples to the aaz repo.
  2. Read the current CLI extension module from aaz-dev.
  3. Bump every command's `version` (and any `waitCommand.version`) to the target version.
  4. PUT the module back, which triggers CLI code generation into the extension repo.

Supports both extensions:
  - cdn        (az cdn ... / az afd ...)
  - front-door (az network front-door ...)

Prerequisites:
  - aaz-dev running on http://127.0.0.1:5000 (use restart_aaz_dev.ps1)
  - azdev venv activated (use_aaz_dev_env.ps1) for `requests` to be available
  - Workspace already Exported (either manually in Web UI, or via --workspace here)

Usage:
    python generate_cli.py --ext cdn        --version 2025-09-01-preview
    python generate_cli.py --ext front-door --version 2025-11-01
    python generate_cli.py --ext front-door --version 2025-11-01 --workspace front-door-2025-11-01
    python generate_cli.py --ext cdn        --version 2025-09-01-preview --dry-run
"""

import argparse
import sys

import requests

BASE_URL = "http://127.0.0.1:5000"

SUPPORTED_EXTS = ("cdn", "front-door")


def export_workspace(workspace):
    url = f"{BASE_URL}/AAZ/Editor/Workspaces/{workspace}/Generate"
    resp = requests.post(url)
    if not resp.ok:
        print(f"ERROR: Export failed ({resp.status_code}): {resp.text}", file=sys.stderr)
        return False
    print(f"Exported workspace: {workspace}")
    return True


def get_module(ext):
    url = f"{BASE_URL}/CLI/Az/Extension/Modules/{ext}"
    resp = requests.get(url)
    if not resp.ok:
        print(f"ERROR: GET {url} failed ({resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)
    return resp.json()


def put_module(ext, data):
    url = f"{BASE_URL}/CLI/Az/Extension/Modules/{ext}"
    resp = requests.put(url, json=data)
    if not resp.ok:
        print(f"ERROR: PUT {url} failed ({resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)


def update_versions(node, new_version, counts):
    """Recursively set every command.version and waitCommand.version to new_version."""
    if "commandGroups" in node and node["commandGroups"]:
        for group in node["commandGroups"].values():
            update_versions(group, new_version, counts)
    if "commands" in node and node["commands"]:
        for cmd in node["commands"].values():
            if "version" in cmd:
                if cmd["version"] != new_version:
                    counts["commands_changed"] += 1
                cmd["version"] = new_version
            counts["commands_total"] += 1
    if "waitCommand" in node and isinstance(node["waitCommand"], dict):
        if "version" in node["waitCommand"]:
            if node["waitCommand"]["version"] != new_version:
                counts["wait_changed"] += 1
            node["waitCommand"]["version"] = new_version


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ext", required=True, choices=SUPPORTED_EXTS,
                        help="CLI extension to generate")
    parser.add_argument("--version", required=True,
                        help="Target API version to pin every command to (e.g. 2025-11-01)")
    parser.add_argument("--workspace",
                        help="Optional: workspace name to Export before generating "
                             "(equivalent to clicking Export in the Web UI)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would change; do not PUT")
    args = parser.parse_args()

    if args.workspace:
        if not export_workspace(args.workspace):
            sys.exit(1)

    print(f"Fetching CLI module: {args.ext}")
    data = get_module(args.ext)

    profiles = data.get("profiles") or {}
    latest = profiles.get("latest")
    if not latest:
        print("ERROR: module has no 'profiles.latest' node; did Export run?", file=sys.stderr)
        sys.exit(1)

    counts = {"commands_total": 0, "commands_changed": 0, "wait_changed": 0}
    update_versions(latest, args.version, counts)

    print(f"Commands in module: {counts['commands_total']}")
    print(f"  version changes:  {counts['commands_changed']}")
    print(f"  waitCommand changes: {counts['wait_changed']}")
    print(f"  target version:   {args.version}")

    if args.dry_run:
        print("Dry-run: skipping PUT.")
        return

    print(f"PUT {BASE_URL}/CLI/Az/Extension/Modules/{args.ext} (triggers code generation)...")
    put_module(args.ext, data)
    print("Done. Review changes with: git -C $env:AAZ_CLI_EXTENSION_PATH status")


if __name__ == "__main__":
    main()
