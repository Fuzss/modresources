#!/usr/bin/env python3
"""
Validate CurseForge and Modrinth distribution data against Mod Resources.

The script compares distribution properties between:

```
<mods-directory>/<mod-folder>/main/versions.json
```

and:

```
<modresources-directory>/mods/<mod-id>.json
```

The Mod Resources file name is determined from the mod folder name by removing
all dashes.

For example:

```
air-hop
```

becomes:

```
airhop.json
```

The script compares all properties under:

```
distributions.curseforge
distributions.modrinth
```

GitHub distributions are intentionally ignored.

Mods without a corresponding Mod Resources JSON file are skipped.

The script does not modify any files and does not perform any Git operations.

Usage:

```
python3 validate_distribution_properties.py \
    <mods-directory> \
    <modresources-mods-directory>
```

Example:

```
python3 validate_distribution_properties.py \
    /Users/user/Lokal/GitHub/mods \
    /Users/user/Lokal/GitHub/modresources/mods
```

For every mismatching property, both values are printed so the discrepancy can
be fixed manually.
"""

import json
import sys
from pathlib import Path

DISTRIBUTION_PLATFORMS = [
"curseforge",
"modrinth",
]

def read_json_file(file_path: Path) -> dict | None:
    """
    Read and parse a JSON file.

    ```
    Args:
        file_path: The JSON file to read.

    Returns:
        The parsed JSON object, or None if the file contains invalid JSON.
    """
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exception:
        print(f"  Invalid JSON: {exception}")
        return None


def get_mod_id(mod_directory: Path) -> str:
    """
    Convert a mod directory name into its Mod Resources file name.

    ```
    Example:

        air-hop -> airhop

    Args:
        mod_directory: The mod directory.

    Returns:
        The corresponding mod ID.
    """
    return mod_directory.name.replace("-", "")


def validate_platform(
    mod_name: str,
    platform: str,
    versions_distributions: dict,
    resources_distributions: dict,
    ) -> int:
    """
    Compare all properties for a distribution platform.

    ```
    Properties present in either source are compared. Missing properties are
    therefore also reported as mismatches.

    Args:
        mod_name: The mod folder name.
        platform: The distribution platform to compare.
        versions_distributions: The distributions object from versions.json.
        resources_distributions: The distributions object from Mod Resources.

    Returns:
        The number of mismatches found.
    """
    versions_platform = versions_distributions.get(platform, {})
    resources_platform = resources_distributions.get(platform, {})

    if not isinstance(versions_platform, dict):
        versions_platform = {}

    if not isinstance(resources_platform, dict):
        resources_platform = {}

    property_names = sorted(
        set(versions_platform) | set(resources_platform)
    )

    mismatch_count = 0

    for property_name in property_names:
        versions_value = versions_platform.get(property_name)
        resources_value = resources_platform.get(property_name)

        if versions_value == resources_value:
            continue

        if mismatch_count == 0:
            print(f"  {platform}:")

        print(f"    Property: {property_name}")
        print(f"    versions.json: {versions_value!r}")
        print(f"    Mod Resources: {resources_value!r}")

        mismatch_count += 1

    return mismatch_count


def main():
    """
    Validate distribution data for every mod in the supplied mods directory.

    ```
    Command line arguments:

        validate_distribution_properties.py \
            <mods-directory> \
            <modresources-mods-directory>
    """
    if len(sys.argv) != 3:
        print(
            f"Usage: {sys.argv[0]} "
            "<mods-directory> "
            "<modresources-mods-directory>"
        )
        sys.exit(1)

    mods_directory = Path(sys.argv[1]).expanduser().resolve()
    resources_directory = Path(sys.argv[2]).expanduser().resolve()

    if not mods_directory.is_dir():
        print(f"Mods directory does not exist: {mods_directory}")
        sys.exit(1)

    if not resources_directory.is_dir():
        print(
            f"Mod Resources directory does not exist: "
            f"{resources_directory}"
        )
        sys.exit(1)

    mod_directories = sorted(
        directory
        for directory in mods_directory.iterdir()
        if directory.is_dir()
    )

    total_mods = 0
    validated_mods = 0
    total_mismatches = 0

    for mod_directory in mod_directories:
        total_mods += 1

        versions_file = (
            mod_directory
            / "main"
            / "versions.json"
        )

        if not versions_file.is_file():
            continue

        mod_id = get_mod_id(mod_directory)

        resources_file = (
            resources_directory
            / f"{mod_id}.json"
        )

        if not resources_file.is_file():
            print(
                f"Skipping {mod_directory.name}: "
                f"{mod_id}.json not found"
            )
            continue

        versions_data = read_json_file(versions_file)

        if versions_data is None:
            print(
                f"Skipping {mod_directory.name}: "
                f"invalid versions.json"
            )
            continue

        resources_data = read_json_file(resources_file)

        if resources_data is None:
            print(
                f"Skipping {mod_directory.name}: "
                f"invalid Mod Resources JSON"
            )
            continue

        versions_distributions = versions_data.get(
            "distributions",
            {},
        )

        resources_distributions = resources_data.get(
            "distributions",
            {},
        )

        if not isinstance(versions_distributions, dict):
            print(
                f"Skipping {mod_directory.name}: "
                f"versions.json distributions is not an object"
            )
            continue

        if not isinstance(resources_distributions, dict):
            print(
                f"Skipping {mod_directory.name}: "
                f"Mod Resources distributions is not an object"
            )
            continue

        mismatch_count = 0

        for platform in DISTRIBUTION_PLATFORMS:
            mismatch_count += validate_platform(
                mod_directory.name,
                platform,
                versions_distributions,
                resources_distributions,
            )

        validated_mods += 1

        if mismatch_count > 0:
            print(
                f"{mod_directory.name}: "
                f"{mismatch_count} mismatch"
                f"{'es' if mismatch_count != 1 else ''}"
            )
            total_mismatches += mismatch_count
        else:
            print(f"{mod_directory.name}: valid")

    print()
    print("Validation complete")
    print(f"Mods found: {total_mods}")
    print(f"Mods validated: {validated_mods}")
    print(f"Total mismatches: {total_mismatches}")


if __name__ == "__main__":
    main()
