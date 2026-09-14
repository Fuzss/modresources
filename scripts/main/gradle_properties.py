#!/usr/bin/env python3
"""Gradle properties loading, updating, and version bumping."""

import json
import os
import re
from functools import lru_cache

from console import error2
from gradle_user_properties import load_gradle_properties


SEMANTIC_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
VERSION_KEYWORDS = {"latest", "patch", "minor", "major"}


def get_properties_key(line: str) -> tuple[str, ...]:
    key = line.split("=", 1)[0].strip()
    return tuple(key.split("."))


def get_matching_parts(first: tuple[str, ...], second: tuple[str, ...]) -> int:
    matching_parts = 0

    for first_part, second_part in zip(first, second):
        if first_part != second_part:
            break

        matching_parts += 1

    return matching_parts


def find_insertion_index(lines: list[str], new_key: str) -> int:
    new_key_parts = get_properties_key(new_key)

    previous_matching_parts = 0

    for index, line in enumerate(lines):
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        current_key = get_properties_key(line)
        matching_parts = get_matching_parts(current_key, new_key_parts)

        if matching_parts < previous_matching_parts:
            return index

        if matching_parts > 0 and current_key > new_key_parts:
            return index

        previous_matching_parts = matching_parts

    return -1


def update_gradle_properties(file_path, updates: dict, remove_predicate=None):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    properties = {}
    updated_lines = []

    for line in lines:
        content = line.strip()
        if "=" not in line:
            updated_lines.append(line)
            continue

        comment = False
        if content.startswith('#'):
            content = content[1:].strip()
            comment = True

        key, value = content.split('=', 1)
        key = key.strip()
        value = value.strip()

        if key in updates:
            updated_value = updates[key]

            if callable(updated_value):
                updated_value = updated_value(value)

            if updated_value == "#":
                comment = True
            elif updated_value is None:
                value = None
            else:
                comment = False
                value = updated_value

            if value is not None:
                updated_lines.append(f'{"#" if comment else ""}{key}={value}\n')
        elif remove_predicate and remove_predicate(key):
            value = None
        else:
            updated_lines.append(line)

        if not comment and value is not None:
            properties[key] = value

    for key, value in updates.items():
        if key in properties or value is None or value == "#":
            continue

        if callable(value):
            error2(f"Missing property {key} in {file_path}, cannot update it automatically")

        line = f"{key}={value}\n"
        index = find_insertion_index(updated_lines, key)
        if index == -1:
            updated_lines.append("\n")
            updated_lines.append(line)
        else:
            updated_lines.insert(index, line)

        properties[key] = value

    if updates or remove_predicate:
        with open(file_path, 'w') as f:
            f.writelines(updated_lines)

    updated_properties = {
        key: value
        for key, value in properties.items()
        if key in updates
    }

    print(json.dumps(updated_properties, indent=2, sort_keys=True))

    return properties


@lru_cache(maxsize=1)
def _cached_gradle_properties():
    return load_gradle_properties()


def find_gradle_property(prop, default=None):
    try:
        gradle_properties = _cached_gradle_properties()
    except FileNotFoundError:
        error2("Missing ~/.gradle/gradle.properties")

    if prop in gradle_properties:
        return gradle_properties[prop]
    elif default is not None:
        return default
    else:
        error2(f"Missing property {prop} in ~/.gradle/gradle.properties")


def bump_version(version, component):
    if not SEMANTIC_VERSION_PATTERN.fullmatch(version):
        error2(
            f"Cannot bump version '{version}', expected semantic version x.y.z"
        )

    major, minor, patch = map(int, version.split("."))

    if component == "major":
        # Minecraft version numbers begin at minor update 1, not 0
        return f"{major + 1}.1.0"
    if component == "minor":
        return f"{major}.{minor + 1}.0"
    if component == "patch":
        return f"{major}.{minor}.{patch + 1}"

    error2(f"Unsupported version component: {component}")


def create_gradle_properties(args, legacy_properties=False):
    properties = {}

    if args.version:
        version_key = "modVersion" if legacy_properties else "mod.version"

        version = args.version.lower()

        if version in {"patch", "minor", "major"}:
            properties[version_key] = lambda property: bump_version(property, version)
        elif version == "latest":
            pass
        elif SEMANTIC_VERSION_PATTERN.fullmatch(version):
            properties[version_key] = version
        else:
            error2(
                f"Invalid version '{args.version}'. Expected semantic version "
                f"(e.g. 26.1.0) or one of: {', '.join(sorted(VERSION_KEYWORDS))}"
            )

    if args.catalog:
        properties["dependenciesVersionCatalog" if legacy_properties else "project.libs"] = args.catalog

    if args.plugins:
        properties["project.plugins"] = args.plugins

    if args.properties:
        for key, value in args.properties:
            properties[key.strip()] = value.strip()

    return properties
