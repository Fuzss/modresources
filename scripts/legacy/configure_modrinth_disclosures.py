from pathlib import Path
import json
import subprocess
import sys
import time


TOGGLE_COORDINATES = (1527, 496)
DISCLOSURE_OPTION_COORDINATES = (690, 735)
TEXT_FIELD_COORDINATES = (890, 840)
SAVE_BUTTON_COORDINATES = (1425, 1180)

DISCLOSURE_TEXT = (
    "LLMs may have assisted in creating or refining some project page texts, "
    "such as summaries, descriptions, and documentation."
)


def run_applescript(script):
    subprocess.run(
        ["osascript", "-e", script],
        check=True,
    )


def click_coordinates(coordinates):
    x, y = coordinates

    run_applescript(
        f'''
        tell application "System Events"
            click at {{{x}, {y}}}
        end tell
        '''
    )


def open_url(url):
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
    with versions_file.open(encoding="utf-8") as file:
        versions = json.load(file)

    return versions.get("distributions", {}).get("modrinth", {}).get("slug")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <root-directory>")
        sys.exit(1)

    root_directory = Path(sys.argv[1]).expanduser().resolve()

    start_project_name = sys.argv[2] if len(sys.argv) > 2 else None

    start_processing = start_project_name is None

    for project_directory in sorted(root_directory.iterdir()):
        if not project_directory.is_dir():
            continue

        project_name = project_directory.name
        print(f"Processing {project_name}")

        if not start_processing:
            if project_name != start_project_name:
                continue

            start_processing = True

        versions_file = project_directory / "main" / "versions.json"

        if not versions_file.is_file():
            continue

        modrinth_slug = get_modrinth_slug(versions_file)

        if modrinth_slug is None:
            continue

        url = f"https://modrinth.com/mod/{modrinth_slug}/settings/disclosures"
        print(f"Opening {url}")

        open_url(url)
        time.sleep(3)

        click_coordinates(TOGGLE_COORDINATES)
        time.sleep(2)

        click_coordinates(DISCLOSURE_OPTION_COORDINATES)
        time.sleep(2)

        run_applescript(
            f'''
            tell application "System Events"
                keystroke tab
            end tell
            '''
        )
        time.sleep(2)

        run_applescript(
            f'''
            tell application "System Events"
                keystroke "{DISCLOSURE_TEXT}"
            end tell
            '''
        )
        time.sleep(2)

        click_coordinates(SAVE_BUTTON_COORDINATES)
        time.sleep(3)


if __name__ == "__main__":
    main()
