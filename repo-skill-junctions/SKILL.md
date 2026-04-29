---
name: repo-skill-junctions
description: "Expose a shared skill directory as a repo-local project skill on Windows by creating a junction under .github/skills and adding a matching entry to .git/info/exclude. Use when wiring a skill from a shared Skills folder into a specific repository such as pwsh, cli, or extension without committing the link. Do NOT use for editing the skill content itself, for user-global ~/.copilot skills, or for Linux/macOS symlink setup."
argument-hint: "Describe the repo and shared skill to link, e.g. 'link Skills/azure-cli-skill into extension'"
---

# Repository Skill Junctions

## Overview

Use this skill when a shared skill lives outside a repository root, but should be discoverable as a project skill inside one specific repository.

The standard Windows pattern is:

1. Create or reuse `<repo>/.github/skills/`
2. Create a junction at `<repo>/.github/skills/<skill-name>` pointing to the shared skill directory
3. Add `/.github/skills/<skill-name>` to `<repo>/.git/info/exclude`
4. Verify both the junction target and `git status`

This keeps the skill available to Copilot in that repository without introducing a tracked repository change.

## Inputs

Collect these inputs if they are not already provided:

1. Target repository root, for example `C:\Users\jingnanxu\source\repos\pwsh`
2. Shared skill directory, for example `C:\Users\jingnanxu\source\repos\Skills\azure-pwsh-skill`
3. Skill name, usually the shared skill folder name such as `azure-pwsh-skill`

Derived paths:

- Repo skill path: `<repo>/.github/skills/<skill-name>`
- Local Git exclude file: `<repo>/.git/info/exclude`

## Preconditions

Before creating anything:

1. Confirm the target repository contains a `.git/` directory.
2. Confirm the shared skill directory exists and contains `SKILL.md`.
3. Inspect whether the repo skill path already exists.

If the target path already exists:

- If it is already the correct junction, leave it in place.
- If it is a different junction, directory, or file, show the current state to the user and wait for approval before replacing it.

## Workflow

### Step 1: Inspect Current State

Check these items first:

```powershell
Test-Path <repo>
Test-Path <shared-skill-dir>
Test-Path <shared-skill-dir>\SKILL.md
Test-Path <repo>\.git
Test-Path <repo>\.github\skills
Test-Path <repo>\.github\skills\<skill-name>
```

If the skill path exists, inspect it with:

```powershell
Get-Item <repo>\.github\skills\<skill-name> | Format-List FullName,Attributes,LinkType,Target
```

### Step 2: Create the Repo Skill Directory

If `<repo>/.github/skills/` does not exist, create it:

```powershell
New-Item -ItemType Directory -Force -Path <repo>\.github\skills | Out-Null
```

### Step 3: Create or Repair the Junction

If the target skill path is missing, create the junction:

```powershell
New-Item -ItemType Junction \
  -Path <repo>\.github\skills\<skill-name> \
  -Target <shared-skill-dir>
```

If the target skill path exists but is wrong:

1. Show the current state to the user.
2. Explain whether it is a stale junction, normal directory, or file.
3. Wait for approval before removing or replacing it.
4. Remove only the conflicting target path, then create the correct junction.

### Step 4: Update Local Git Excludes

Use the repository-local exclude file so the junction does not appear in `git status`.

Required entry:

```gitignore
/.github/skills/<skill-name>
```

Append it only if it is absent. Do not modify the tracked `.gitignore` unless the user explicitly asks.

### Step 5: Verify the Result

Verify the junction:

```powershell
Get-Item <repo>\.github\skills\<skill-name> | Format-List FullName,LinkType,Target
```

Verify Git state:

```powershell
git -C <repo> status --short
```

Success criteria:

- `LinkType` is `Junction`
- `Target` points to the intended shared skill directory
- `git status --short` does not show `.github/skills/<skill-name>`

## Approval Rules

Get explicit approval before any of these actions:

- Replacing an existing path under `.github/skills/<skill-name>`
- Removing a stale junction, file, or directory
- Modifying `.git/info/exclude`

If the path does not exist yet, it is fine to propose the exact create commands and then proceed after approval.

## Constraints

- Use this workflow only on Windows with PowerShell and NTFS junction support.
- Prefer junctions over copying the skill directory, so the shared skill remains single-source.
- Do not use tracked repository files for local-only setup when `.git/info/exclude` is sufficient.
- Do not broaden ignore rules beyond the exact skill path unless the user asks.

## Troubleshooting

### Junction creation fails

Possible causes:

- The path already exists
- Permissions prevent creating the junction
- The target directory does not exist

Action:

1. Re-inspect the target path.
2. Confirm the target shared skill directory exists.
3. If permissions are the issue, tell the user elevated privileges or policy changes may be required.

### Git still shows the skill path

Possible causes:

- The exclude entry is missing
- The entry path is incorrect
- The path was already staged previously

Action:

1. Re-read `.git/info/exclude`
2. Confirm the entry is exactly `/.github/skills/<skill-name>`
3. Check whether the path was already staged and tell the user if manual unstage is needed

### Copilot still does not discover the skill

Possible causes:

- The repository context is not the expected one
- The skill folder does not contain `SKILL.md`
- The skill frontmatter is invalid

Action:

1. Verify the repository root being used by the editor
2. Verify the junction target contains `SKILL.md`
3. Inspect the skill frontmatter for required fields such as `name` and `description`

## Examples

- "Link Skills/azure-pwsh-skill into pwsh as a local project skill"
- "Expose Skills/azure-cli-skill inside extension without changing tracked git files"
- "Create a repo-local skill junction for cli and hide it from git status"