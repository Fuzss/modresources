#!/usr/bin/env python3

import json
import subprocess
import sys
import time
from pathlib import Path


def load_gradle_properties():
    path = Path.home() / ".gradle" / "gradle.properties"
    properties = {}

    with path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                properties[key.strip()] = value.strip()

    return properties


def get_modrinth_id(versions_file):
    with versions_file.open(encoding="utf-8") as file:
        versions = json.load(file)

    return versions.get("distributions", {}).get("modrinth", {}).get("id")


def main():
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

        mod_id = project_name.replace("-", "")

        body_file = (
            resources_path
            / "pages"
            / "out"
            / mod_id
            / "modrinth.html"
        )

        if not body_file.is_file():
            print(f"Skipping {project_name}: no Modrinth body file found")
            continue

        body = body_file.read_text(encoding="utf-8")

        result = subprocess.run(
            [
                "curl",
                "--fail-with-body",
                "--silent",
                "--show-error",
                "--request",
                "PATCH",
                f"https://api.modrinth.com/v2/project/{modrinth_id}",
                "--header",
                f"Authorization: Bearer {modrinth_token}",
                "--header",
                "Content-Type: application/json",
                "--data-binary",
                json.dumps({"body": body}),
            ],
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
