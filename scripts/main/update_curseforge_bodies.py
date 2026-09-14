#!/usr/bin/env python3
"""Batch-update CurseForge project descriptions across mod repositories.

Purpose: for every mod directory, publish the generated CurseForge page as
that project's CurseForge description by driving the web editor through macOS
UI automation.

Entry points: run directly as
``python3 update_curseforge_bodies.py [project]``; not imported by ``main.py``.

Side effects: reads ``versions.json`` and the generated page tree, copies HTML
to the macOS clipboard with ``pbcopy``, opens Safari, and clicks/keystrokes the
CurseForge editor through ``osascript`` and System Events. Performs no git
operations.

Constraints: macOS only (``pbcopy``, ``osascript``, Safari, and Accessibility
permissions). Projects are processed alphabetically; the optional project
argument resumes from that project onward. The fixed screen coordinates below
depend on the browser window size and page layout and may need updating.

Usage:
    python3 update_curseforge_bodies.py               # every project
    python3 update_curseforge_bodies.py example-mod   # resume at example-mod

Inputs:
    Reads ``fuzs.multiloader.project.mods`` and
    ``fuzs.multiloader.project.resources`` from
    ``~/.gradle/gradle.properties``. For ``<mods>/<project>`` it reads
    ``main/versions.json`` for the ``distributions.curseforge.slug`` and the
    body from
    ``<resources>/pages/out/<project>/curseforge.html``. The
    editor URL is
    ``https://legacy.curseforge.com/minecraft/mc-mods/<slug>/settings/description``.
    Projects missing any of those files or properties are skipped.
"""

from pathlib import Path
import json
import subprocess
import sys
import time

from gradle_user_properties import load_gradle_properties


# Screen coordinates for the CurseForge description editor.
#
# These coordinates depend on the current browser window size and layout.
# If the CurseForge page layout changes, these may need to be updated.
SOURCE_MODE_BUTTON_COORDINATES = (635, 455)
OK_BUTTON_COORDINATES = (1250, 950)
SAVE_CHANGES_BUTTON_COORDINATES = (1555, 855)


def run_applescript(script):
    """Run a raw AppleScript source string through ``osascript -e``.

    Side effects: launches ``osascript``.
    """

    subprocess.run(
        ["osascript", "-e", script],
        check=True,
    )


def click_coordinates(coordinates):
    """Click the screen position ``(x, y)`` through System Events.

    Side effects: moves the cursor and clicks via ``osascript``.
    """

    x, y = coordinates

    run_applescript(
        f'''
        tell application "System Events"
            click at {{{x}, {y}}}
        end tell
        '''
    )


def open_url(url):
    """Activate Safari and navigate to ``url`` through its address bar.

    Side effects: focuses Safari and sends keystrokes through System Events.
    """

    run_applescript(
        f'''
        tell application "Safari"
            activate
        end tell

        tell application "System Events"
            keystroke "l" using {{command down}}
            delay 1
            keystroke "{url}"
            delay 1
            key code 36
        end tell
        '''
    )


def get_curseforge_slug(versions_file):
    """Return ``distributions.curseforge.slug`` from a project's versions.json.

    Returns None when the slug is absent.

    Side effects: reads ``versions_file``.
    """

    versions = json.loads(versions_file.read_text(encoding="utf-8"))

    return versions.get("distributions", {}).get("curseforge", {}).get("slug")


def replace_description():
    """Replace the focused editor content with the clipboard via Cmd+A/Cmd+V.

    The source editor focuses its own text field, so no click or Tab
    navigation is required.

    Side effects: sends keystrokes through System Events.
    """

    run_applescript(
        '''
        tell application "System Events"
            keystroke "a" using {command down}
            delay 0.5
            keystroke "v" using {command down}
        end tell
        '''
    )


def main():
    """Update every eligible CurseForge project description.

    Side effects: see the module docstring. Exits with code 1 when a requested
    starting project does not exist.
    """
    properties = load_gradle_properties()

    mods_path = Path(properties["fuzs.multiloader.project.mods"])
    resources_path = Path(properties["fuzs.multiloader.project.resources"])

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

        curseforge_slug = get_curseforge_slug(versions_file)

        if not curseforge_slug:
            continue

        description_file = (
            resources_path
            / "pages"
            / "out"
            / project_name
            / "curseforge.html"
        )

        if not description_file.is_file():
            print(f"Skipping {project_name}: no CurseForge body file found")
            continue

        description = description_file.read_text(encoding="utf-8")

        url = (
            f"https://legacy.curseforge.com/minecraft/mc-mods/"
            f"{curseforge_slug}/settings/description"
        )

        print(f"Opening {url}")

        # pbcopy avoids a Python clipboard dependency; the HTML is pasted
        # into the source editor later with Command+V.
        subprocess.run(
            ["pbcopy"],
            input=description,
            text=True,
            check=True,
        )

        open_url(url)
        time.sleep(3)

        print("Opening source editor")
        click_coordinates(SOURCE_MODE_BUTTON_COORDINATES)
        time.sleep(2)

        print("Replacing description")
        replace_description()
        time.sleep(1)

        print("Closing source editor")
        click_coordinates(OK_BUTTON_COORDINATES)
        time.sleep(2)

        print("Saving changes")
        click_coordinates(SAVE_CHANGES_BUTTON_COORDINATES)
        time.sleep(3)

        print(f"Updated {project_name}")

    if start_project_name is not None and not start_processing:
        print(f"Project not found: {start_project_name}")
        sys.exit(1)


if __name__ == "__main__":
    main()
