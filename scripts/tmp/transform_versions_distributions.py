#!/usr/bin/env python3
"""
Transform versions.json distribution properties for multiple mods.

The script searches every mod directory inside the supplied mods directory.

For each mod, it performs the following steps:

1. Reads <mod>/main/versions.json.

2. Reads the top level "properties" object.

3. Converts properties in the following format:

   "distributions.curseforge.id": "323071"
   "distributions.curseforge.slug": "air-hop"
   "distributions.github.slug": "air-hop"
   "distributions.modrinth.id": "g1eaCZgs"
   "distributions.modrinth.slug": "air-hop"

   into:

   "distributions": {
   "curseforge": {
   "id": "323071",
   "slug": "air-hop"
   },
   "github": {
   "slug": "air-hop"
   },
   "modrinth": {
   "id": "g1eaCZgs",
   "slug": "air-hop"
   }
   }

4. Removes the top level "properties" object.

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
│   └── main/
│       └── versions.json
├── another-mod/
│   └── main/
│       └── versions.json
└── ...
```

Usage:

```
python3 transform_versions_distributions.py <mods-directory>
```

Example:

```
python3 transform_versions_distributions.py \
    /Users/user/Lokal/GitHub/mods
```

Restarting from a specific mod:

```
python3 transform_versions_distributions.py \
    /Users/user/Lokal/GitHub/mods \
    air-hop
```

Mod directories are processed alphabetically. When a start folder is provided,
all folders alphabetically before it are skipped. The specified folder itself is
included, allowing the script to safely resume from a previously interrupted
mod.

Git requirements:

Each <mod>/main directory must be a valid Git working tree with a configured
remote and upstream branch.

For every changed versions.json, the script executes:

```
git pull
git add versions.json
git commit -m "Transform version distributions"
git push
```

Only versions.json is added and committed by this script.
"""

import json
import subprocess
import sys
from pathlib import Path

PROPERTY_PREFIX = "distributions."

def run_git_command(
directory: Path,
*arguments: str,
) -> subprocess.CompletedProcess:
    """
    Run a Git command in the supplied directory.

    ```
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


def transform_properties(
properties: dict,
) -> dict[str, dict[str, str]]:
    """
    Transform flat distribution properties into nested distribution objects.

    ```
    For example:

        distributions.curseforge.id=323071

    becomes:

        {
            "curseforge": {
                "id": "323071"
            }
        }

    Only properties beginning with "distributions." are transformed.

    Args:
        properties: The existing top level "properties" object.

    Returns:
        A nested distributions object.
    """
    distributions = {}

    for property_name, value in properties.items():
        if not property_name.startswith(PROPERTY_PREFIX):
            continue

        property_parts = property_name.split(".")

        # Expected format:
        #
        # distributions.<platform>.<property>
        #
        # For example:
        #
        # distributions.curseforge.id
        if len(property_parts) != 3:
            print(
                f"  Ignoring unsupported property format: "
                f"{property_name}"
            )
            continue

        _, platform, property_key = property_parts

        if platform not in distributions:
            distributions[platform] = {}

        distributions[platform][property_key] = value

    return distributions


def main():
    """
    Transform distribution properties for every mod in the supplied directory.

    ```
    Command line arguments:

        transform_versions_distributions.py <mods-directory> [start-folder]

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

    mod_directories = sorted(
        directory
        for directory in mods_directory.iterdir()
        if directory.is_dir()
    )

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

        properties = versions_data.get("properties")

        if properties is None:
            print("  Skipping: no properties object")
            continue

        if not isinstance(properties, dict):
            print("  Skipping: properties is not an object")
            continue

        distributions = transform_properties(properties)

        if not distributions:
            print("  Skipping: no distribution properties found")
            continue

        # Remove the old flat property structure and replace it with the
        # nested distribution structure.
        del versions_data["properties"]
        versions_data["distributions"] = distributions

        # sort_keys=True recursively sorts all existing and newly created
        # JSON object keys alphabetically.
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

        print("  Transformed versions.json")

        git_status = run_git_command(
            main_directory,
            "status",
            "--porcelain",
            "versions.json",
        )

        if not git_status.stdout.strip():
            print("  No Git changes detected")
            continue

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
            "Transform version distributions",
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
