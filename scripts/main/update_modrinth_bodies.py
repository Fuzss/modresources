#!/usr/bin/env python3
"""
Update Modrinth project descriptions for multiple mods.

The script searches every mod directory inside the configured mods directory.

For each mod, it performs the following steps:

1. Reads <mod>/main/versions.json.

2. Reads the Modrinth project ID from:

   "distributions": {
       "modrinth": {
           "id": "..."
       }
   }

3. Uses the configured resources directory to locate the generated Modrinth
   project description:

   <resources>/pages/out/<mod-id>/modrinth.html

   The mod ID is derived from the mod directory name by removing hyphens.

   For example:

   easy-shulker-boxes
       ->
   easyshulkerboxes

4. Reads the generated HTML description using UTF-8 encoding.

5. Updates the Modrinth project description through the Modrinth API.

   The request is sent as:

   PATCH https://api.modrinth.com/v2/project/<project-id>

   The generated HTML is supplied as the "body" property of the JSON request
   body.

6. Authenticates the API request using the Modrinth token configured in the
   user's Gradle properties.

7. Uses curl instead of a Python HTTP library so that the script does not
   require any additional Python dependencies.

8. Prints an error when the API request fails and continues processing the
   remaining projects instead of aborting the entire script.

9. Waits briefly after each successful update to avoid sending requests for
   multiple projects immediately after one another.

Only projects with all required files and properties are processed. Projects
without versions.json, a Modrinth project ID, or a generated Modrinth HTML file
are skipped.

Projects are processed alphabetically.

Restarting from a specific project:

    python3 update_modrinth_bodies.py example-mod

When a starting project is provided, all projects alphabetically before it are
skipped. The specified project itself is included, allowing the script to
resume from a previously interrupted project.

Without an argument, all projects are processed:

    python3 update_modrinth_bodies.py

The script reads the following properties from the user's Gradle properties
file:

    ~/.gradle/gradle.properties

    fuzs.multiloader.project.mods
    fuzs.multiloader.project.resources
    fuzs.multiloader.project.modrinth.token

The first property identifies the directory containing the mod repositories.
The second property identifies the resources repository containing the
generated project pages. The third property contains the token used to
authenticate with the Modrinth API.

Expected directory structure:

    mods/
    ├── easy-shulker-boxes/
    │   └── main/
    │       └── versions.json
    ├── another-mod/
    │   └── main/
    │       └── versions.json
    └── ...

    resources/
    └── pages/
        └── out/
            └── easyshulkerboxes/
                └── modrinth.html

API request:

The generated description is sent to:

    https://api.modrinth.com/v2/project/<project-id>

with the following headers:

    Authorization: Bearer <modrinth-token>
    Content-Type: application/json

The request body contains:

    {
        "body": "<generated HTML>"
    }

The script uses curl's --fail-with-body option so that HTTP errors result in a
nonzero exit code while still preserving the response body for error reporting.

The script does not perform any version control operations. It does not run
git pull, git add, git commit, git push, or any other Git command.
"""

import json
import subprocess
import sys
import time
from pathlib import Path


def load_gradle_properties():
    """Load user level Gradle properties from ~/.gradle/gradle.properties."""

    path = Path.home() / ".gradle" / "gradle.properties"
    properties = {}

    with path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            # Ignore empty lines and comments.
            if not line or line.startswith("#"):
                continue

            # Gradle properties use key=value syntax.
            if "=" in line:
                key, value = line.split("=", 1)
                properties[key.strip()] = value.strip()

    return properties


def get_modrinth_id(versions_file):
    """
    Read the Modrinth project ID from a project's versions.json.

    The expected structure is:

        distributions:
          modrinth:
            id: ...
    """

    with versions_file.open(encoding="utf-8") as file:
        versions = json.load(file)

    return versions.get("distributions", {}).get("modrinth", {}).get("id")


def main():
    # These paths and the Modrinth token are configured globally in the
    # user's Gradle properties.
    #
    # The mods directory contains the individual mod repositories.
    # The resources directory contains the generated project page files.
    properties = load_gradle_properties()

    mods_path = Path(properties["fuzs.multiloader.project.mods"])
    resources_path = Path(properties["fuzs.multiloader.project.resources"])
    modrinth_token = properties["fuzs.multiloader.project.modrinth.token"]

    # Optionally start with a specific project:
    #
    #     update_modrinth_bodies.py example-mod
    #
    # Without an argument, all projects are processed.
    start_project_name = sys.argv[1] if len(sys.argv) > 1 else None

    # Without a starting project, process every project.
    # Otherwise, skip projects until the requested project is reached.
    start_processing = start_project_name is None

    # Process every project directory in alphabetical order.
    for project_directory in sorted(mods_path.iterdir()):
        if not project_directory.is_dir():
            continue

        project_name = project_directory.name

        # If a starting project was specified, skip projects until it is found.
        if not start_processing:
            if project_name != start_project_name:
                continue

            start_processing = True

        # Every project must have its versions.json in the main directory.
        versions_file = project_directory / "main" / "versions.json"

        if not versions_file.is_file():
            continue

        # The Modrinth project ID is required for the API request.
        modrinth_id = get_modrinth_id(versions_file)

        if not modrinth_id:
            continue

        # The generated page files use the mod ID as their directory name.
        # The mod ID is derived from the project name by removing hyphens.
        mod_id = project_name.replace("-", "")

        # This is the generated HTML that should become the Modrinth
        # project description.
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

        # Update the project description through the Modrinth API.
        #
        # curl is used instead of a Python HTTP library so the script has
        # no additional Python dependencies.
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

        # curl returns a nonzero exit code when the request fails.
        # Continue processing the remaining projects instead of aborting
        # the entire script.
        if result.returncode != 0:
            print(f"Failed to update {project_name}: {result.stderr}")
            continue

        print(f"Updated {project_name}")

        # Avoid sending requests for multiple projects immediately after
        # one another.
        time.sleep(0.5)

    # If a starting project was supplied but could not be found, report it
    # instead of silently doing nothing.
    if start_project_name is not None and not start_processing:
        print(f"Project not found: {start_project_name}")
        sys.exit(1)


if __name__ == "__main__":
    main()
