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
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:5000"

SUPPORTED_EXTS = ("cdn", "front-door")

EXTENSION_AAZ_PATHS = {
    "cdn": ["src/cdn/azext_cdn/aaz/latest"],
    "front-door": ["src/front-door/azext_front_door/aaz/latest"],
}

COMMAND_MODEL_PATHS = {
    "cdn": ["Commands/cdn", "Commands/afd"],
    "front-door": ["Commands/network/front-door"],
}

UPDATE_EXAMPLE_PATTERNS = {
    ".py": re.compile(r"(?P<prefix>\s*:example:\s+)(?P<verb>Creates?|creates?)(?P<rest>\b.*)"),
    ".md": re.compile(r"(?P<prefix>\s*-\s+)(?P<verb>Creates?|creates?)(?P<rest>\b.*)"),
}


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


def _update_verb(verb):
    if verb.lower() == "creates":
        fixed = "updates"
    else:
        fixed = "update"
    if verb[0].isupper():
        return fixed.capitalize()
    return fixed


def _fix_update_examples_in_file(path):
    pattern = UPDATE_EXAMPLE_PATTERNS.get(path.suffix.lower())
    if not pattern or path.name not in ("_update.py", "_update.md"):
        return 0

    with path.open("r", encoding="utf-8", newline="") as file:
        text = file.read()
    replacements = 0

    def repl(match):
        nonlocal replacements
        replacements += 1
        return f"{match.group('prefix')}{_update_verb(match.group('verb'))}{match.group('rest')}"

    fixed = pattern.sub(repl, text)
    if replacements:
        with path.open("w", encoding="utf-8", newline="") as file:
            file.write(fixed)
    return replacements


def _iter_existing_roots(base, relative_paths):
    if not base:
        return
    base_path = Path(base)
    for rel_path in relative_paths:
        path = base_path / rel_path
        if path.exists():
            yield path


def fix_update_examples(ext):
    """Fix generated update examples that still say Create/Creates."""
    roots = []
    roots.extend(_iter_existing_roots(os.environ.get("AAZ_CLI_EXTENSION_PATH"), EXTENSION_AAZ_PATHS[ext]))
    roots.extend(_iter_existing_roots(os.environ.get("AAZ_PATH"), COMMAND_MODEL_PATHS[ext]))

    total = 0
    files = 0
    for root in roots:
        for suffix in ("*.py", "*.md"):
            for path in root.rglob(suffix):
                count = _fix_update_examples_in_file(path)
                if count:
                    total += count
                    files += 1

    print(f"Update example fix: {total} replacement(s) across {files} file(s).")


def _get_azdev_command():
    azdev = shutil.which("azdev")
    if azdev:
        return azdev
    candidate = Path(sys.executable).with_name("azdev.exe")
    if candidate.exists():
        return str(candidate)
    candidate = Path(sys.executable).with_name("azdev")
    if candidate.exists():
        return str(candidate)
    return "azdev"


def ask_run_linter(run_linter, no_run_linter):
    """Return whether to run linter after generation."""
    if run_linter and no_run_linter:
        raise ValueError("run-linter and no-run-linter options cannot be used together")
    if run_linter:
        return True
    if no_run_linter:
        return False
    if not sys.stdin.isatty():
        print("\nSkipping linter prompt because stdin is not interactive.")
        print("Use --run-linter to run linter automatically.")
        return False

    while True:
        answer = input("\nRun linter now? [y/N]: ").strip().lower()
        if answer in ("", "n", "no"):
            return False
        if answer in ("y", "yes"):
            return True
        print("Please answer y or n.")


def run_linter(ext):
    """Run the relevant azdev linter for an extension."""
    azdev = _get_azdev_command()
    command = [azdev, "linter", ext]
    print(f"\nRunning: {' '.join(command)}")
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        print(f"ERROR: command failed with exit code {result.returncode}: {' '.join(command)}", file=sys.stderr)
        return False
    return True


def maybe_run_linter(ext, run_linter=False, no_run_linter=False):
    try:
        should_run = ask_run_linter(run_linter, no_run_linter)
    except ValueError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    if should_run and not run_linter(ext):
        sys.exit(1)


def maybe_run_checks(ext, run_checks=False, no_run_checks=False):
    """Backward-compatible alias: checks now mean linter only, never tests."""
    maybe_run_linter(ext, run_checks, no_run_checks)


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
    parser.add_argument("--no-fix-examples", action="store_true",
                        help="Skip post-generation fix for update examples that say Create/Creates")
    parser.add_argument("--run-linter", action="store_true",
                        help="After generation, run azdev linter without prompting")
    parser.add_argument("--no-run-linter", action="store_true",
                        help="After generation, skip the linter prompt")
    parser.add_argument("--run-checks", dest="run_linter", action="store_true",
                        help="Deprecated alias for --run-linter; tests are not run by this script")
    parser.add_argument("--no-run-checks", dest="no_run_linter", action="store_true",
                        help="Deprecated alias for --no-run-linter")
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
    if not args.no_fix_examples:
        fix_update_examples(args.ext)
    print("Done. Review changes with: git -C $env:AAZ_CLI_EXTENSION_PATH status")
    maybe_run_linter(args.ext, args.run_linter, args.no_run_linter)


if __name__ == "__main__":
    main()
