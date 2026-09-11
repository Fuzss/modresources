#!/usr/bin/env python3

from pathlib import Path
import json
import subprocess
import sys
import time


# Screen coordinates for the Modrinth disclosure settings page.
#
# These coordinates depend on the current browser window size and layout.
# If the Modrinth page layout changes, these may need to be updated.
TOGGLE_COORDINATES = (1527, 496)
DISCLOSURE_OPTION_COORDINATES = (690, 735)
TEXT_FIELD_COORDINATES = (890, 840)
SAVE_BUTTON_COORDINATES = (1425, 1180)

DISCLOSURE_TEXT = (
    "LLMs may have assisted in creating or refining some project page texts, "
    "such as summaries, descriptions, and documentation."
)


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


def get_modrinth_slug(versions_file):
    """
    Read the Modrinth project slug from a project's versions.json.

    The expected structure is:

        distributions:
          modrinth:
            slug: ...
    """

    with versions_file.open(encoding="utf-8") as file:
        versions = json.load(file)

    return versions.get("distributions", {}).get("modrinth", {}).get("slug")


def main():
    # The root directory contains the individual mod projects.
    #
    # Usage:
    #
    #     script.py <root-directory>
    #
    # An optional second argument can be used to start processing at a
    # specific project:
    #
    #     script.py <root-directory> SomeMod
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <root-directory>")
        sys.exit(1)

    root_directory = Path(sys.argv[1]).expanduser().resolve()

    start_project_name = sys.argv[2] if len(sys.argv) > 2 else None

    # Without a starting project, process every project.
    # Otherwise, skip projects until the requested project is reached.
    start_processing = start_project_name is None

    # Process every project directory in alphabetical order.
    for project_directory in sorted(root_directory.iterdir()):
        if not project_directory.is_dir():
            continue

        project_name = project_directory.name
        print(f"Processing {project_name}")

        # If a starting project was specified, skip projects until it is found.
        if not start_processing:
            if project_name != start_project_name:
                continue

            start_processing = True

        # Every project must have its versions.json in the main directory.
        versions_file = project_directory / "main" / "versions.json"

        if not versions_file.is_file():
            continue

        # The Modrinth slug is required to construct the disclosure settings URL.
        modrinth_slug = get_modrinth_slug(versions_file)

        if modrinth_slug is None:
            continue

        # Open the project's Modrinth disclosure settings page.
        url = f"https://modrinth.com/mod/{modrinth_slug}/settings/disclosures"
        print(f"Opening {url}")

        open_url(url)
        time.sleep(3)

        # Enable the disclosure section.
        click_coordinates(TOGGLE_COORDINATES)
        time.sleep(2)

        # Select the disclosure option for AI assisted project page text.
        click_coordinates(DISCLOSURE_OPTION_COORDINATES)
        time.sleep(2)

        # The text field is reached through keyboard navigation after
        # selecting the disclosure option.
        run_applescript(
            '''
            tell application "System Events"
                keystroke tab
            end tell
            '''
        )
        time.sleep(2)

        # Enter the disclosure text into the selected text field.
        run_applescript(
            f'''
            tell application "System Events"
                keystroke "{DISCLOSURE_TEXT}"
            end tell
            '''
        )
        time.sleep(2)

        # Save the disclosure settings.
        click_coordinates(SAVE_BUTTON_COORDINATES)
        time.sleep(3)

    # If a starting project was supplied but could not be found, report it
    # instead of silently doing nothing.
    if start_project_name is not None and not start_processing:
        print(f"Project not found: {start_project_name}")
        sys.exit(1)


if __name__ == "__main__":
    main()
