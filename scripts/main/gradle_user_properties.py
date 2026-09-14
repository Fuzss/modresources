#!/usr/bin/env python3
"""Load user-level Gradle properties from ~/.gradle/gradle.properties.

Shared by the core CLI and the standalone body-update scripts so the parsing
logic lives in one place.
"""

import os


def load_gradle_properties():
    path = os.path.expanduser("~/.gradle/gradle.properties")
    properties = {}

    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                properties[key.strip()] = value.strip()

    return properties
