"""
Bump the extension version in setup.py and prepend a HISTORY.rst entry.

Covers Step 8 of the swagger-upgrade workflow for both extensions:
  - cdn        -> extension/src/cdn/{setup.py,HISTORY.rst}
  - front-door -> extension/src/front-door/{setup.py,HISTORY.rst}

Extension root resolution order:
  1. --extension-path CLI argument
  2. AAZ_CLI_EXTENSION_PATH environment variable
  3. AAZ_REPOS_ROOT/extension (fallback)

Usage:
    # Explicit message, one bullet per --message
    python update_history.py --ext front-door --version 2.3.0 \\
        --message "Bump swagger version to 2025-11-01" \\
        --message "Add support for managed rule set exceptions"

    # Shortcut: auto-generate a swagger-bump bullet
    python update_history.py --ext cdn --version 3.1.0 --swagger-version 2025-09-01-preview

    # Preview without writing
    python update_history.py --ext front-door --version 2.3.0 \\
        --swagger-version 2025-11-01 --dry-run
"""

import argparse
import os
import re
import sys
from pathlib import Path

SUPPORTED_EXTS = ("cdn", "front-door")

VERSION_RE = re.compile(r'^(?P<indent>\s*)VERSION\s*=\s*["\'](?P<version>[^"\']+)["\']', re.MULTILINE)
SEMVER_RE = re.compile(r'^\d+\.\d+\.\d+([a-zA-Z0-9.+-]*)$')


def resolve_extension_root(extension_path_arg):
    root = extension_path_arg or os.environ.get("AAZ_CLI_EXTENSION_PATH")
    if not root:
        repo_root = os.environ.get("AAZ_REPOS_ROOT")
        if repo_root:
            root = os.path.join(repo_root, "extension")
    if not root or not os.path.isdir(root):
        print("ERROR: extension repo not found.", file=sys.stderr)
        print("  Use --extension-path <path>, set AAZ_CLI_EXTENSION_PATH,", file=sys.stderr)
        print("  or run: . .github\\azure-cli-skill\\scripts\\use_aaz_dev_env.ps1", file=sys.stderr)
        sys.exit(1)
    return Path(root)


def bump_setup_py(setup_path, new_version, dry_run):
    text = setup_path.read_text(encoding="utf-8")
    match = VERSION_RE.search(text)
    if not match:
        print(f"ERROR: could not find VERSION = \"...\" in {setup_path}", file=sys.stderr)
        sys.exit(1)

    old_version = match.group("version")
    if old_version == new_version:
        print(f"setup.py already at {new_version}, leaving unchanged.")
        return old_version

    new_text = text[:match.start()] + f'{match.group("indent")}VERSION = "{new_version}"' + text[match.end():]

    print(f"setup.py: {old_version} -> {new_version}")
    if not dry_run:
        setup_path.write_text(new_text, encoding="utf-8")
    return old_version


def format_history_entry(version, messages):
    # Underline must be at least as long as the title; keep 6 '+' to match existing style,
    # but grow if version is longer (e.g. "10.0.0" = 6 chars still fits 6 '+').
    underline = "+" * max(6, len(version))
    lines = [version, underline]
    for msg in messages:
        msg = msg.strip()
        if not msg:
            continue
        if not msg.startswith("* "):
            msg = "* " + msg
        lines.append(msg)
    return "\n".join(lines) + "\n"


def prepend_history(history_path, version, messages, dry_run):
    text = history_path.read_text(encoding="utf-8")

    # Detect whether this version is already at the top
    # Strategy: locate the first version header (a line that looks like semver followed by a "+++" underline)
    entry = format_history_entry(version, messages)

    # Find the first version header after the release-history banner.
    header_re = re.compile(r'^(?P<ver>\d+\.\d+\.\d+\S*)\n\++\s*$', re.MULTILINE)
    first = header_re.search(text)
    if first and first.group("ver") == version:
        print(f"HISTORY.rst: entry for {version} already present at top; leaving unchanged.")
        return

    if not first:
        # No existing entries; append after the banner.
        insert_at = len(text)
        new_text = text.rstrip() + "\n\n" + entry
    else:
        insert_at = first.start()
        new_text = text[:insert_at] + entry + "\n" + text[insert_at:]

    print(f"HISTORY.rst: prepend entry for {version} ({len(messages)} bullet(s))")
    if not dry_run:
        history_path.write_text(new_text, encoding="utf-8")


def build_messages(args):
    msgs = list(args.message or [])
    if args.swagger_version:
        swagger_msg = f"Bump swagger version to {args.swagger_version}"
        if swagger_msg not in msgs:
            msgs.insert(0, swagger_msg)
    if not msgs:
        print("ERROR: provide at least one --message or --swagger-version", file=sys.stderr)
        sys.exit(1)
    return msgs


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ext", required=True, choices=SUPPORTED_EXTS)
    parser.add_argument("--version", required=True,
                        help='New extension version (e.g. "2.3.0"). Written to setup.py and HISTORY.rst header.')
    parser.add_argument("--message", action="append",
                        help="Changelog bullet. Repeat for multiple bullets. Leading '* ' is optional.")
    parser.add_argument("--swagger-version",
                        help='Shortcut: adds "Bump swagger version to <value>" as the first bullet.')
    parser.add_argument("--extension-path",
                        help="Path to azure-cli-extensions repo root (else AAZ_CLI_EXTENSION_PATH / AAZ_REPOS_ROOT/extension).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print planned changes; do not write files.")
    args = parser.parse_args()

    if not SEMVER_RE.match(args.version):
        print(f"ERROR: --version must look like X.Y.Z, got {args.version!r}", file=sys.stderr)
        sys.exit(1)

    ext_root = resolve_extension_root(args.extension_path)
    ext_dir = ext_root / "src" / args.ext

    setup_path = ext_dir / "setup.py"
    history_path = ext_dir / "HISTORY.rst"

    for p in (setup_path, history_path):
        if not p.is_file():
            print(f"ERROR: missing file: {p}", file=sys.stderr)
            sys.exit(1)

    messages = build_messages(args)

    print(f"Extension: {args.ext}  (dir: {ext_dir})")
    print(f"Target version: {args.version}")
    for m in messages:
        print(f"  bullet: {m}")
    if args.dry_run:
        print("(dry-run)")

    bump_setup_py(setup_path, args.version, args.dry_run)
    prepend_history(history_path, args.version, messages, args.dry_run)

    if args.dry_run:
        print("Dry-run complete. No files were modified.")
    else:
        print("Done. Review with:")
        print(f"  git -C {ext_root} diff -- src/{args.ext}/setup.py src/{args.ext}/HISTORY.rst")


if __name__ == "__main__":
    main()
