"""
Update gradle.properties files across multiple Minecraft mod projects.

The script expects the following directory structure:

    <root directory>/
        project-a/
            <version>/
                gradle.properties
        project-b/
            <version>/
                gradle.properties

Only direct child directories of the root directory are considered projects.

Usage:

    python3 update_gradle_properties.py <root directory> <version>

Example:

    python3 update_gradle_properties.py \
        /Users/user/Lokal/GitHub/mods \
        1.21.1
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


# The Gradle configuration block used by newer project versions.
NEW_GRADLE_CONFIGURATION = """\
org.gradle.caching=true
org.gradle.configuration-cache=false
org.gradle.daemon=true
org.gradle.jvmargs=-Xmx4G
org.gradle.parallel=true
loom.ignoreDependencyLoomVersionValidation=true
"""


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        The parsed root directory and Minecraft version.
    """

    parser = argparse.ArgumentParser(
        description="Update gradle.properties files across multiple projects."
    )

    parser.add_argument(
        "root_directory",
        type=Path,
        help="Directory containing the individual project directories.",
    )
    parser.add_argument(
        "version",
        help="Minecraft version directory to process, for example 1.21.1.",
    )

    return parser.parse_args()


def replace_forge_config_api_port(content: str) -> str:
    """
    Replace the old Fabric specific Forge Config API Port artifact name.

    This replacement intentionally applies to the entire file rather than
    only to individual property values.
    """

    return content.replace(
        "forge-config-api-port-fabric",
        "forge-config-api-port",
    )


def update_dependency_properties(content: str) -> str:
    """
    Update dependency related properties.

    Changes:
        dependenciesVersionCatalog is always set to 1.21.1-SNAPSHOT.

        dependenciesPuzzlesLibVersion is commented out.

        dependenciesMinPuzzlesLibVersion is commented out.

    The PuzzlesLib property values are preserved. Existing comments are
    normalized to a single leading hash.
    """

    updated_lines: list[str] = []

    for line in content.splitlines():
        stripped_line = line.strip()

        version_catalog_match = re.match(
            r"^#*dependenciesVersionCatalog=.*$",
            stripped_line,
        )

        if version_catalog_match:
            updated_lines.append(
                "dependenciesVersionCatalog=1.21.1-SNAPSHOT"
            )
            continue

        puzzles_lib_match = re.match(
            r"^#*(dependencies(?:PuzzlesLibVersion|MinPuzzlesLibVersion)=.*)$",
            stripped_line,
        )

        if puzzles_lib_match:
            updated_lines.append(
                f"#{puzzles_lib_match.group(1)}"
            )
            continue

        updated_lines.append(line)

    return "\n".join(updated_lines)


def remove_optional_dependencies(content: str) -> str:
    """
    Remove all optional dependency properties and their section heading.

    Every property beginning with 'dependenciesOptional' is removed,
    regardless of its suffix or value.

    The '# Optional Dependencies' heading is also removed when present.
    """

    updated_lines: list[str] = []

    for line in content.splitlines():
        stripped_line = line.strip()

        if stripped_line == "# Optional Dependencies":
            continue

        if stripped_line.startswith("dependenciesOptional"):
            continue

        updated_lines.append(line)

    return "\n".join(updated_lines)


def replace_gradle_configuration(content: str) -> str:
    """
    Replace the legacy Gradle configuration block with the new block.

    The legacy block consists of:

        org.gradle.jvmargs=-Xmx4G
        org.gradle.daemon=false
        copyBuildJar=true

    The block must appear consecutively and is expected to end before a
    blank line or at the end of the file.

    A warning is printed when the expected legacy block cannot be found,
    allowing future format changes to be detected instead of silently
    producing an incomplete migration.
    """

    old_configuration_pattern = re.compile(
        r"(?m)^org\.gradle\.jvmargs=-Xmx4G\n"
        r"org\.gradle\.daemon=false\n"
        r"copyBuildJar=true"
        r"(?=\n[ \t]*\n|\Z)"
    )

    updated_content, replacements = old_configuration_pattern.subn(
        NEW_GRADLE_CONFIGURATION.rstrip(),
        content,
        count=1,
    )

    if replacements == 0:
        print("  Warning: Legacy Gradle configuration block not found.")

    return updated_content


def normalize_empty_lines(content: str) -> str:
    """
    Normalize whitespace in the resulting file.

    Multiple consecutive empty lines are reduced to one empty line.
    Trailing whitespace is removed from every line.

    The resulting file always ends with exactly one newline and never with
    an additional blank line.
    """

    lines = [
        line.rstrip()
        for line in content.splitlines()
    ]

    normalized_lines: list[str] = []
    previous_line_was_empty = False

    for line in lines:
        is_empty = not line

        if is_empty and previous_line_was_empty:
            continue

        normalized_lines.append(line)
        previous_line_was_empty = is_empty

    while normalized_lines and not normalized_lines[-1]:
        normalized_lines.pop()

    return "\n".join(normalized_lines) + "\n"


def update_gradle_properties(content: str) -> str:
    """
    Apply the complete gradle.properties migration.

    Individual transformations are intentionally kept in separate methods.
    This makes future migrations easier to maintain, modify, or remove
    without affecting unrelated transformations.
    """

    content = replace_forge_config_api_port(content)
    content = update_dependency_properties(content)
    content = remove_optional_dependencies(content)
    content = replace_gradle_configuration(content)
    content = normalize_empty_lines(content)

    return content


def process_project(
        project_directory: Path,
        version: str,
) -> bool | None:
    """
    Process the gradle.properties file for one project.

    Returns:
        True if the file was modified.

        False if the file already contained the expected content.

        None if the project does not contain the requested version.
    """

    file_path = project_directory / version / "gradle.properties"

    if not file_path.is_file():
        return None

    original_content = file_path.read_text(encoding="utf-8")
    updated_content = update_gradle_properties(original_content)

    if updated_content == original_content:
        return False

    file_path.write_text(updated_content, encoding="utf-8")
    return True


def process_projects(
        root_directory: Path,
        version: str,
) -> None:
    """
    Process every direct project directory in the root directory.

    Projects without '<version>/gradle.properties' are skipped.
    """

    updated_count = 0
    unchanged_count = 0
    skipped_count = 0

    for project_directory in sorted(root_directory.iterdir()):
        if not project_directory.is_dir():
            continue

        result = process_project(project_directory, version)

        if result is None:
            skipped_count += 1
            continue

        if result:
            print(f"Updated:   {project_directory.name}")
            updated_count += 1
        else:
            print(f"Unchanged: {project_directory.name}")
            unchanged_count += 1

    print()
    print(f"Updated:   {updated_count}")
    print(f"Unchanged: {unchanged_count}")
    print(f"Skipped:   {skipped_count}")


def main() -> None:
    """
    Parse arguments and start processing projects.
    """

    arguments = parse_arguments()

    root_directory = arguments.root_directory.expanduser().resolve()

    if not root_directory.is_dir():
        raise SystemExit(
            f"Root directory does not exist or is not a directory: "
            f"{root_directory}"
        )

    process_projects(root_directory, arguments.version)


if __name__ == "__main__":
    main()
