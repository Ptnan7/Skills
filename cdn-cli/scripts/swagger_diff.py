"""
Compare two swagger API versions for a given extension and summarize changes.

Parses the readme.md to find the input files for each tag, then diffs the
JSON schemas to report new/removed operations, model changes, and enum updates.

Supports two extensions:
  - cdn:        CDN / AFD (Microsoft.Cdn)
  - front-door: Front Door classic WAF (Microsoft.Network/frontdoor)

Usage:
    python swagger_diff.py --ext front-door --old 2025-10-01 --new 2025-11-01
    python swagger_diff.py --ext cdn --old 2024-02-01 --new 2025-09-01-preview

Requires: AAZ_SWAGGER_PATH environment variable pointing to a local
          azure-rest-api-specs clone.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Extension profiles: swagger module path relative to specification/
EXTENSION_PROFILES = {
    "cdn": {
        "readme_path": "cdn/resource-manager/Microsoft.Cdn/Cdn",
    },
    "front-door": {
        "readme_path": "frontdoor/resource-manager/Microsoft.Network/FrontDoor",
    },
}


def get_swagger_root():
    """Get swagger repo root from env or default."""
    root = os.environ.get("AAZ_SWAGGER_PATH")
    if not root:
        # Fallback: try repo root detection
        repo_root = os.environ.get("AAZ_REPOS_ROOT")
        if repo_root:
            root = os.path.join(repo_root, "swagger")
    if not root or not os.path.isdir(root):
        print("ERROR: AAZ_SWAGGER_PATH not set or not a valid directory.", file=sys.stderr)
        print("Run: . .github\\cdn-cli\\scripts\\use_aaz_dev_env.ps1", file=sys.stderr)
        sys.exit(1)
    return root


def parse_readme_tags(readme_path):
    """Parse readme.md to extract tag -> input-file mappings."""
    with open(readme_path, encoding="utf-8") as f:
        content = f.read()

    tags = {}
    # Match tag blocks: ### Tag: <name> ... ```yaml ... input-file: ... ```
    tag_pattern = re.compile(
        r"###\s+Tag:\s+([\w\-]+)\s*\n"
        r".*?"
        r"```yaml[^\n]*\n(.*?)```",
        re.DOTALL,
    )
    for match in tag_pattern.finditer(content):
        tag_name = match.group(1)
        yaml_block = match.group(2)
        files = re.findall(r"-\s+(\S+\.json)", yaml_block)
        if files:
            tags[tag_name] = files
    return tags


def version_to_tag(version, tags):
    """Find the tag name that matches a version string like '2025-11-01'."""
    # Try exact patterns: package-YYYY-MM, package-preview-YYYY-MM, package-YYYY-MM-DD
    version_parts = version.split("-")

    # For preview versions like 2025-09-01-preview
    if "preview" in version:
        candidates = [
            f"package-preview-{version_parts[0]}-{version_parts[1]}",
            f"package-{version}",
        ]
    else:
        candidates = [
            f"package-{version_parts[0]}-{version_parts[1]}",
            f"package-{version}",
        ]

    for candidate in candidates:
        if candidate in tags:
            return candidate

    # Fallback: search for version substring in tag names
    for tag_name in tags:
        if version_parts[0] in tag_name and version_parts[1] in tag_name:
            return tag_name

    return None


def load_swagger_files(base_dir, file_list):
    """Load and merge multiple swagger JSON files into a single schema."""
    merged = {"paths": {}, "definitions": {}}
    for filepath in file_list:
        full_path = os.path.join(base_dir, filepath)
        if not os.path.exists(full_path):
            print(f"  WARNING: File not found: {full_path}", file=sys.stderr)
            continue
        with open(full_path, encoding="utf-8") as f:
            data = json.load(f)
        merged["paths"].update(data.get("paths", {}))
        merged["definitions"].update(data.get("definitions", {}))
    return merged


def extract_operations(paths):
    """Extract operation list from paths: {(method, path): operation_info}."""
    ops = {}
    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() in ("get", "put", "post", "delete", "patch", "head", "options"):
                op_id = details.get("operationId", "")
                ops[(method.upper(), path)] = {
                    "operationId": op_id,
                    "description": details.get("description", ""),
                    "parameters": [
                        p.get("name", "") for p in details.get("parameters", [])
                    ],
                }
    return ops


def extract_enum_values(definitions):
    """Extract enum values from all definitions."""
    enums = {}
    for name, schema in definitions.items():
        _collect_enums(name, schema, enums)
    return enums


def _collect_enums(prefix, schema, enums):
    """Recursively collect enum definitions."""
    if "enum" in schema:
        enum_name = schema.get("x-ms-enum", {}).get("name", prefix)
        enums[enum_name] = set(str(v) for v in schema["enum"])
    for prop_name, prop_schema in schema.get("properties", {}).items():
        _collect_enums(f"{prefix}.{prop_name}", prop_schema, enums)
    if "items" in schema:
        _collect_enums(f"{prefix}[]", schema["items"], enums)
    if "allOf" in schema:
        for i, sub in enumerate(schema["allOf"]):
            _collect_enums(f"{prefix}.allOf[{i}]", sub, enums)


def extract_model_properties(definitions):
    """Extract property names and required fields for each model."""
    models = {}
    for name, schema in definitions.items():
        props = set(schema.get("properties", {}).keys())
        required = set(schema.get("required", []))
        models[name] = {"properties": props, "required": required}
    return models


def diff_operations(old_ops, new_ops):
    """Compare operations between old and new."""
    old_keys = set(old_ops.keys())
    new_keys = set(new_ops.keys())

    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)

    modified = []
    for key in sorted(old_keys & new_keys):
        old_params = set(old_ops[key]["parameters"])
        new_params = set(new_ops[key]["parameters"])
        if old_params != new_params:
            modified.append({
                "operation": key,
                "added_params": sorted(new_params - old_params),
                "removed_params": sorted(old_params - new_params),
            })

    return added, removed, modified


def diff_models(old_models, new_models):
    """Compare model definitions."""
    old_names = set(old_models.keys())
    new_names = set(new_models.keys())

    added = sorted(new_names - old_names)
    removed = sorted(old_names - new_names)

    modified = []
    for name in sorted(old_names & new_names):
        old_props = old_models[name]["properties"]
        new_props = new_models[name]["properties"]
        old_req = old_models[name]["required"]
        new_req = new_models[name]["required"]
        if old_props != new_props or old_req != new_req:
            modified.append({
                "model": name,
                "added_props": sorted(new_props - old_props),
                "removed_props": sorted(old_props - new_props),
                "added_required": sorted(new_req - old_req),
                "removed_required": sorted(old_req - new_req),
            })

    return added, removed, modified


def diff_enums(old_enums, new_enums):
    """Compare enum definitions."""
    changes = []
    all_names = sorted(set(old_enums.keys()) | set(new_enums.keys()))
    for name in all_names:
        old_vals = old_enums.get(name, set())
        new_vals = new_enums.get(name, set())
        if old_vals != new_vals:
            changes.append({
                "enum": name,
                "added": sorted(new_vals - old_vals),
                "removed": sorted(old_vals - new_vals),
            })
    return changes


def print_report(old_version, new_version, ops_added, ops_removed, ops_modified,
                 models_added, models_removed, models_modified, enum_changes):
    """Print a human-readable diff summary."""
    print(f"\n{'='*70}")
    print(f"  Swagger Diff: {old_version} -> {new_version}")
    print(f"{'='*70}\n")

    # Operations
    print("## Operations\n")
    if ops_added:
        print(f"  Added ({len(ops_added)}):")
        for method, path in ops_added:
            print(f"    + {method} {path}")
    if ops_removed:
        print(f"\n  Removed ({len(ops_removed)}):")
        for method, path in ops_removed:
            print(f"    - {method} {path}")
    if ops_modified:
        print(f"\n  Modified ({len(ops_modified)}):")
        for m in ops_modified:
            method, path = m["operation"]
            print(f"    ~ {method} {path}")
            if m["added_params"]:
                print(f"        new params: {', '.join(m['added_params'])}")
            if m["removed_params"]:
                print(f"        removed params: {', '.join(m['removed_params'])}")
    if not ops_added and not ops_removed and not ops_modified:
        print("  No operation changes.")

    # Models
    print(f"\n## Models\n")
    if models_added:
        print(f"  Added ({len(models_added)}):")
        for name in models_added:
            print(f"    + {name}")
    if models_removed:
        print(f"\n  Removed ({len(models_removed)}):")
        for name in models_removed:
            print(f"    - {name}")
    if models_modified:
        print(f"\n  Modified ({len(models_modified)}):")
        for m in models_modified:
            print(f"    ~ {m['model']}")
            if m["added_props"]:
                print(f"        new properties: {', '.join(m['added_props'])}")
            if m["removed_props"]:
                print(f"        removed properties: {', '.join(m['removed_props'])}")
            if m["added_required"]:
                print(f"        new required: {', '.join(m['added_required'])}")
            if m["removed_required"]:
                print(f"        no longer required: {', '.join(m['removed_required'])}")
    if not models_added and not models_removed and not models_modified:
        print("  No model changes.")

    # Enums
    print(f"\n## Enums\n")
    if enum_changes:
        for ec in enum_changes:
            print(f"  ~ {ec['enum']}")
            if ec["added"]:
                print(f"      new values: {', '.join(ec['added'])}")
            if ec["removed"]:
                print(f"      removed values: {', '.join(ec['removed'])}")
    else:
        print("  No enum changes.")

    # Breaking changes summary
    breaking = []
    if ops_removed:
        breaking.append(f"  - {len(ops_removed)} operation(s) removed")
    if models_removed:
        breaking.append(f"  - {len(models_removed)} model(s) removed")
    for m in models_modified:
        if m["removed_props"]:
            breaking.append(f"  - {m['model']}: properties removed ({', '.join(m['removed_props'])})")
        if m["added_required"]:
            breaking.append(f"  - {m['model']}: new required fields ({', '.join(m['added_required'])})")
    for ec in enum_changes:
        if ec["removed"]:
            breaking.append(f"  - {ec['enum']}: enum values removed ({', '.join(ec['removed'])})")

    print(f"\n## Breaking Changes\n")
    if breaking:
        for b in breaking:
            print(b)
    else:
        print("  None detected.")
    print()


def main():
    parser = argparse.ArgumentParser(description="Compare swagger API versions")
    parser.add_argument("--ext", required=True, choices=list(EXTENSION_PROFILES.keys()),
                        help="Extension to compare (cdn or front-door)")
    parser.add_argument("--old", required=True, help="Old API version (e.g. 2025-10-01)")
    parser.add_argument("--new", required=True, help="New API version (e.g. 2025-11-01)")
    args = parser.parse_args()

    profile = EXTENSION_PROFILES[args.ext]
    swagger_root = get_swagger_root()
    spec_dir = os.path.join(swagger_root, "specification", profile["readme_path"])
    readme_path = os.path.join(spec_dir, "readme.md")

    if not os.path.exists(readme_path):
        print(f"ERROR: readme.md not found at {readme_path}", file=sys.stderr)
        sys.exit(1)

    tags = parse_readme_tags(readme_path)

    old_tag = version_to_tag(args.old, tags)
    new_tag = version_to_tag(args.new, tags)

    if not old_tag:
        print(f"ERROR: Could not find tag for old version '{args.old}'", file=sys.stderr)
        print(f"  Available tags: {', '.join(sorted(tags.keys()))}", file=sys.stderr)
        sys.exit(1)
    if not new_tag:
        print(f"ERROR: Could not find tag for new version '{args.new}'", file=sys.stderr)
        print(f"  Available tags: {', '.join(sorted(tags.keys()))}", file=sys.stderr)
        sys.exit(1)

    print(f"Old tag: {old_tag} -> files: {tags[old_tag]}")
    print(f"New tag: {new_tag} -> files: {tags[new_tag]}")

    old_schema = load_swagger_files(spec_dir, tags[old_tag])
    new_schema = load_swagger_files(spec_dir, tags[new_tag])

    old_ops = extract_operations(old_schema["paths"])
    new_ops = extract_operations(new_schema["paths"])
    ops_added, ops_removed, ops_modified = diff_operations(old_ops, new_ops)

    old_models = extract_model_properties(old_schema["definitions"])
    new_models = extract_model_properties(new_schema["definitions"])
    models_added, models_removed, models_modified = diff_models(old_models, new_models)

    old_enums = extract_enum_values(old_schema["definitions"])
    new_enums = extract_enum_values(new_schema["definitions"])
    enum_changes = diff_enums(old_enums, new_enums)

    print_report(
        args.old, args.new,
        ops_added, ops_removed, ops_modified,
        models_added, models_removed, models_modified,
        enum_changes,
    )


if __name__ == "__main__":
    main()
