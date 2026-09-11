#!/usr/bin/env python3

from pathlib import Path
import json
import subprocess
import sys
import time


# Screen coordinates for the CurseForge description editor.
#
# These coordinates depend on the current browser window size and layout.
# If the CurseForge page layout changes, these may need to be updated.
SOURCE_MODE_BUTTON_COORDINATES = (635, 455)
OK_BUTTON_COORDINATES = (1250, 950)
SAVE_CHANGES_BUTTON_COORDINATES = (1555, 855)


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


def run_applescript(script):
    """Execute an AppleScript using macOS's osascript command."""

    subprocess.run(
        ["osascript", "-e", script],
        check=True,
    )


def click_coordinates(coordinates):
    """Click a specific screen position using macOS accessibility APIs."""

    x, y = coordinates

    run_applescript(
        f'''
        tell application "System Events"
            click at {{{x}, {y}}}
        end tell
        '''
    )


def open_url(url):
    """
    Activate Safari and navigate to the supplied URL.

    The URL is entered through the browser address bar rather than opening
    a new browser process or relying on Safari specific URL APIs.
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
    """
    Read the CurseForge project slug from a project's versions.json.

    The expected structure is:

        distributions:
          curseforge:
            slug: ...
    """

    versions = json.loads(versions_file.read_text(encoding="utf-8"))

    return versions.get("distributions", {}).get("curseforge", {}).get("slug")


def replace_description():
    """
    Replace the currently selected description with the clipboard contents.

    The CurseForge source editor automatically focuses its text field when
    opened, so no additional click or Tab navigation is required.

    Command+A selects the existing HTML and Command+V pastes the new HTML
    that was previously copied to the macOS clipboard.
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
    # These paths are configured globally in the user's Gradle properties.
    #
    # The mods directory contains the individual mod repositories.
    # The resources directory contains the generated project page files.
    properties = load_gradle_properties()

    mods_path = Path(properties["fuzs.multiloader.project.mods"])
    resources_path = Path(properties["fuzs.multiloader.project.resources"])

    # Optionally start with a specific project:
    #
    #     update_curseforge_bodies.py example-mod
    #
    # Without an argument, all projects are processed.
    start_project_name = sys.argv[1] if len(sys.argv) > 1 else None
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

        # The CurseForge slug is required to construct the settings URL.
        curseforge_slug = get_curseforge_slug(versions_file)

        if curseforge_slug is None:
            continue

        # The generated page files use the mod ID as their directory name.
        # The mod ID is derived from the project name by removing hyphens.
        mod_id = project_name.replace("-", "")

        # This is the generated HTML that should become the CurseForge
        # project description.
        description_file = (
            resources_path
            / "pages"
            / "out"
            / mod_id
            / "curseforge.html"
        )

        if not description_file.is_file():
            print(f"Skipping {project_name}: no CurseForge body file found")
            continue

        description = description_file.read_text(encoding="utf-8")

        # Construct the legacy CurseForge description settings page.
        url = (
            f"https://legacy.curseforge.com/minecraft/mc-mods/"
            f"{curseforge_slug}/settings/description"
        )

        print(f"Opening {url}")

        # Copy the generated HTML to the macOS clipboard.
        #
        # pbcopy is part of macOS and avoids adding a Python clipboard
        # dependency. The HTML is pasted into the CurseForge source editor
        # later using Command+V.
        subprocess.run(
            ["pbcopy"],
            input=description,
            text=True,
            check=True,
        )

        # Open the CurseForge settings page.
        open_url(url)
        time.sleep(3)

        # Switch from the visual editor to the HTML source editor.
        print("Opening source editor")
        click_coordinates(SOURCE_MODE_BUTTON_COORDINATES)
        time.sleep(2)

        # The source editor automatically focuses its text field.
        # Replace its contents with the generated HTML from the clipboard.
        print("Replacing description")
        replace_description()
        time.sleep(1)

        # Click OK to close the source editor and apply the new description
        # to the visual editor.
        print("Closing source editor")
        click_coordinates(OK_BUTTON_COORDINATES)
        time.sleep(2)

        # Click the page's Save Changes button to permanently save the
        # modified project description.
        print("Saving changes")
        click_coordinates(SAVE_CHANGES_BUTTON_COORDINATES)
        time.sleep(3)

        print(f"Updated {project_name}")

    # If a starting project was supplied but could not be found, report it
    # instead of silently doing nothing.
    if start_project_name is not None and not start_processing:
        print(f"Project not found: {start_project_name}")
        sys.exit(1)


if __name__ == "__main__":
    main()
