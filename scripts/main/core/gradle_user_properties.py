#!/usr/bin/env python3
"""Read user-level Gradle properties.

Purpose: parse ``~/.gradle/gradle.properties`` in one place so the core CLI and
the standalone body-update scripts read the same configuration the same way.

Entry points: ``gradle_properties.find_gradle_property`` and the
``tools/update_curseforge_bodies.py`` / ``tools/update_modrinth_bodies.py``
scripts.

Side effects: reads ``~/.gradle/gradle.properties``.

Constraints: standard library only. The ``core/`` modules import it directly;
the ``tools/`` scripts add ``<scripts/main>/../core`` to ``sys.path`` first and
import it by bare name. The file must exist; a missing file propagates
``FileNotFoundError``.
"""

import os


def load_gradle_properties():
    """Return ``~/.gradle/gradle.properties`` as a flat ``{key: value}`` dict.

    Blank lines and lines starting with ``#`` are ignored; only the first
    ``=`` on a line separates key from value.

    Raises:
        FileNotFoundError: when ``~/.gradle/gradle.properties`` does not exist.

    Side effects: reads the user's Gradle properties file.
    """
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
