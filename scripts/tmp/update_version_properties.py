#!/usr/bin/env python3
"""
Synchronize selected Gradle properties with versions.json for multiple mods.

The script searches every mod directory inside the supplied mods directory.
For each mod, it performs the following steps:

1. Reads <mod>/main/versions.json.
2. Finds the branch whose support type is "primary".
3. Reads <mod>/<primary branch>/gradle.properties.
4. Copies selected distribution properties into the top level "properties"
   object in versions.json.
5. Sorts all JSON object keys alphabetically when writing the file.
6. If versions.json changed:
   a. Pulls the latest changes from the remote.
   b. Adds versions.json to Git.
   c. Commits the change.
   d. Pushes the commit to the remote.

Expected directory structure:

```
mods/
├── air-hop/
│   ├── main/
│   │   └── versions.json
│   └── 26.2.x/
│       └── gradle.properties
├── another-mod/
│   ├── main/
│   │   └── versions.json
│   └── 26.1.x/
│       └── gradle.properties
└── ...
```

The primary branch is determined from versions.json, for example:

```
{
  "branches": {
    "26.1.x": "maintained",
    "26.2.x": "primary"
  }
}
```

In this example, the script reads:

```
<mod>/26.2.x/gradle.properties
```

The following properties are copied if they are present:

```
distributions.curseforge.id
distributions.curseforge.slug
distributions.github.slug
distributions.modrinth.id
distributions.modrinth.slug
```

Example resulting versions.json:

```
{
  "branches": {
    "26.1.x": "maintained",
    "26.2.x": "primary"
  },
  "properties": {
    "distributions.curseforge.id": "323071",
    "distributions.curseforge.slug": "air-hop",
    "distributions.github.slug": "air-hop",
    "distributions.modrinth.id": "g1eaCZgs",
    "distributions.modrinth.slug": "air-hop"
  }
}
```

Usage:

```
python3 update_versions_properties.py <mods-directory>
```

Example:

```
python3 update_versions_properties.py /Users/henning/Lokal/GitHub/mods
```

Restarting from a specific mod:

If the script stops or fails partway through the directory list, provide the
mod folder name as the optional second argument:

```
python3 update_versions_properties.py \
    /Users/henning/Lokal/GitHub/mods \
    air-hop
```

The script sorts mod directories alphabetically and skips every directory whose
name comes alphabetically before the supplied start folder. The start folder
itself is included and processed again.

This allows safely restarting from the mod where processing stopped.

Git requirements:

Each <mod>/main directory must be a valid Git working tree with a configured
remote and upstream branch. The script runs Git commands from this directory.

For every changed versions.json, the script executes:

```
git pull
git add versions.json
git commit -m "Update version properties"
git push
```

Important:

The script only commits versions.json. Other uncommitted files in the repository
are not added by the script.

If git pull, git add, git commit, or git push fails, an error is printed and
the script continues with the next mod.

Potential reasons for Git commands to fail include:

```
* Merge conflicts.
* Local changes conflicting with remote changes.
* Missing upstream configuration.
* Authentication failures.
* Network problems.
```

JSON formatting:

All JSON object keys are sorted alphabetically through sort_keys=True.
This includes existing keys and nested objects such as "branches" and
"properties".
"""

import json
import subprocess
import sys
from pathlib import Path

# Gradle property names that are copied from the primary branch's
# gradle.properties into the "properties" object in versions.json.

PROPERTY_NAMES = [
    "distributions.curseforge.id",
    "distributions.curseforge.slug",
    "distributions.github.slug",
    "distributions.modrinth.id",
    "distributions.modrinth.slug",
]

def read_gradle_properties(file_path: Path) -> dict[str, str]:
    """
    Read simple key=value entries from a Gradle properties file.


    Empty lines and lines beginning with "#" or "!" are ignored.

    Args:
        file_path: The gradle.properties file to read.

    Returns:
        A mapping containing all parsed property names and values.
    """
    properties = {}

    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or line.startswith("!"):
            continue

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        properties[key.strip()] = value.strip()

    return properties


def run_git_command(directory: Path, *arguments: str) -> subprocess.CompletedProcess:
    """
    Run a Git command in the supplied directory.

    Output is captured so callers can inspect the exit code and display errors.

    Args:
        directory: The Git working tree in which to run the command.
        arguments: Arguments passed to Git.

    Returns:
        The completed subprocess result.
    """
    return subprocess.run(
        ["git", *arguments],
        cwd=directory,
        text=True,
        capture_output=True,
    )


def main():
    """
    Synchronize distribution properties for every mod in the supplied directory.

    Command line arguments:

        update_versions_properties.py <mods-directory> [start-folder]

    The optional start folder allows processing to resume from a specific mod.
    Mod directories are processed alphabetically.
    """
    if len(sys.argv) not in (2, 3):
        print(f"Usage: {sys.argv[0]} <mods-directory> [start-folder]")
        sys.exit(1)

    mods_directory = Path(sys.argv[1]).expanduser().resolve()
    start_folder = sys.argv[2] if len(sys.argv) == 3 else None

    if not mods_directory.is_dir():
        print(f"Directory does not exist: {mods_directory}")
        sys.exit(1)

    # Collect mod directories alphabetically to ensure predictable processing
    # and allow restarting from a known folder.
    mod_directories = sorted(
        directory
        for directory in mods_directory.iterdir()
        if directory.is_dir()
    )

    # Skip all directories alphabetically before the requested restart point.
    # The requested start folder itself remains included.
    if start_folder is not None:
        mod_directories = [
            directory
            for directory in mod_directories
            if directory.name >= start_folder
        ]

    for mod_directory in mod_directories:
        print(f"Processing {mod_directory.name}")

        main_directory = mod_directory / "main"
        versions_file = main_directory / "versions.json"

        # Mods without a main/versions.json are not managed by this script.
        if not versions_file.is_file():
            print("  Skipping: main/versions.json not found")
            continue

        try:
            versions_data = json.loads(
                versions_file.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError as exception:
            print(
                f"  Skipping: invalid versions.json ({exception})"
            )
            continue

        branches = versions_data.get("branches", {})

        # The primary branch determines which gradle.properties file provides
        # the distribution metadata.
        primary_branch = next(
            (
                branch
                for branch, support_type in branches.items()
                if support_type == "primary"
            ),
            None,
        )

        if primary_branch is None:
            print("  Skipping: no primary branch")
            continue

        gradle_properties_file = (
            mod_directory / primary_branch / "gradle.properties"
        )

        if not gradle_properties_file.is_file():
            print(
                f"  Skipping: "
                f"{primary_branch}/gradle.properties not found"
            )
            continue

        gradle_properties = read_gradle_properties(
            gradle_properties_file
        )

        # Only copy explicitly supported distribution properties.
        # sorted() guarantees alphabetical insertion order before JSON output.
        copied_properties = {
            property_name: gradle_properties[property_name]
            for property_name in sorted(PROPERTY_NAMES)
            if property_name in gradle_properties
        }

        if not copied_properties:
            print("  Skipping: no matching properties")
            continue

        versions_data["properties"] = copied_properties

        # sort_keys=True recursively sorts all JSON object keys, including
        # pre-existing objects that are unrelated to this script.
        new_contents = json.dumps(
            versions_data,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        ) + "\n"

        old_contents = versions_file.read_text(encoding="utf-8")

        if old_contents == new_contents:
            print("  No changes")
            continue

        versions_file.write_text(
            new_contents,
            encoding="utf-8",
        )

        print("  Updated versions.json")

        # Confirm that versions.json actually appears as modified before
        # performing any Git operations.
        git_status = run_git_command(
            main_directory,
            "status",
            "--porcelain",
            "versions.json",
        )

        if not git_status.stdout.strip():
            print("  No Git changes detected")
            continue

        # Update the local main branch before committing the generated file.
        result = run_git_command(
            main_directory,
            "pull",
        )

        if result.returncode != 0:
            print(f"  git pull failed: {result.stderr.strip()}")
            continue

        result = run_git_command(
            main_directory,
            "add",
            "versions.json",
        )

        if result.returncode != 0:
            print(f"  git add failed: {result.stderr.strip()}")
            continue

        result = run_git_command(
            main_directory,
            "commit",
            "-m",
            "Update version properties",
        )

        if result.returncode != 0:
            print(f"  git commit failed: {result.stderr.strip()}")
            continue

        result = run_git_command(
            main_directory,
            "push",
        )

        if result.returncode != 0:
            print(f"  git push failed: {result.stderr.strip()}")
            continue

        print("  Committed and pushed successfully")


if __name__ == "__main__":
    main()
