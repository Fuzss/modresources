#!/usr/bin/env python3
"""Batch-update Modrinth project descriptions across mod repositories.

Purpose: for every mod directory, publish the generated Modrinth page to the
Modrinth API as that project's description.

Entry points: run directly as
``python3 update_modrinth_bodies.py [project]``; not imported by ``main.py``.

Side effects: reads ``versions.json`` and the generated page tree, then sends
an HTTP ``PATCH`` to ``https://api.modrinth.com/v2/project/<id>`` with
``curl``. Performs no git operations.

Constraints: requires ``curl`` and network access; otherwise standard library.
Projects are processed alphabetically; the optional project argument resumes
from that project onward. The ``Authorization: Bearer`` header is passed
through a curl config file on stdin so the token never appears in the process
argument list, and ``--fail-with-body`` keeps the response body for error
reporting. A failed request is reported and skipped instead of aborting the
batch.

Usage:
    python3 update_modrinth_bodies.py               # every project
    python3 update_modrinth_bodies.py example-mod   # resume at example-mod

Inputs:
    Reads ``fuzs.multiloader.project.mods``,
    ``fuzs.multiloader.project.resources``, and
    ``fuzs.multiloader.project.modrinth.token`` from
    ``~/.gradle/gradle.properties``. For ``<mods>/<project>`` it reads
    ``main/versions.json`` for the ``distributions.modrinth.id`` and the body
    from
    ``<resources>/pages/out/<project>/modrinth.html``.
    Projects missing any of those files or properties are skipped.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

from gradle_user_properties import load_gradle_properties


def get_modrinth_id(versions_file):
    """Return ``distributions.modrinth.id`` from a project's versions.json.

    Returns None when the ID is absent.

    Side effects: reads ``versions_file``.
    """

    with versions_file.open(encoding="utf-8") as file:
        versions = json.load(file)

    return versions.get("distributions", {}).get("modrinth", {}).get("id")


def main():
    """Update every eligible Modrinth project description.

    Side effects: see the module docstring. Exits with code 1 when a requested
    starting project does not exist.
    """
    properties = load_gradle_properties()

    mods_path = Path(properties["fuzs.multiloader.project.mods"])
    resources_path = Path(properties["fuzs.multiloader.project.resources"])
    modrinth_token = properties["fuzs.multiloader.project.modrinth.token"]

    start_project_name = sys.argv[1] if len(sys.argv) > 1 else None
    start_processing = start_project_name is None

    for project_directory in sorted(mods_path.iterdir()):
        if not project_directory.is_dir():
            continue

        project_name = project_directory.name

        if not start_processing:
            if project_name != start_project_name:
                continue

            start_processing = True

        versions_file = project_directory / "main" / "versions.json"

        if not versions_file.is_file():
            continue

        modrinth_id = get_modrinth_id(versions_file)

        if not modrinth_id:
            continue

        body_file = (
            resources_path
            / "pages"
            / "out"
            / project_name
            / "modrinth.html"
        )

        if not body_file.is_file():
            print(f"Skipping {project_name}: no Modrinth body file found")
            continue

        body = body_file.read_text(encoding="utf-8")

        # curl avoids a Python HTTP dependency; the token goes through a
        # stdin config file so it stays out of the process argument list.
        curl_config = f'header = "Authorization: Bearer {modrinth_token}"\n'

        result = subprocess.run(
            [
                "curl",
                "--fail-with-body",
                "--silent",
                "--show-error",
                "--config",
                "-",
                "--request",
                "PATCH",
                f"https://api.modrinth.com/v2/project/{modrinth_id}",
                "--header",
                "Content-Type: application/json",
                "--data-binary",
                json.dumps({"body": body}),
            ],
            input=curl_config,
            text=True,
            capture_output=True,
        )

        if result.returncode != 0:
            print(f"Failed to update {project_name}: {result.stderr}")
            continue

        print(f"Updated {project_name}")

        time.sleep(0.5)

    if start_project_name is not None and not start_processing:
        print(f"Project not found: {start_project_name}")
        sys.exit(1)


if __name__ == "__main__":
    main()
