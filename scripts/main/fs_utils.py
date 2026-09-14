#!/usr/bin/env python3
"""Filesystem, text, and license-file helpers.

Purpose: centralize the file and directory operations used by the CLI and the
workspace migration routines: probing subprojects, copying from templates,
moving and removing paths, text/regex replacement, and copyright-year bumps.

Entry points: imported by ``main.py``, ``git_ops.py``, ``changelog.py``,
``workspace_upgrade.py``, and ``validation.py``.

Side effects: reads, writes, copies, moves, and deletes files and directories
under the supplied paths. Most helpers print a progress line; ``error2`` calls
terminate the process.

Constraints: standard library only. Directory copies are staged in a temporary
sibling directory so a failed copy cannot delete an existing destination.
"""

import os
import re
import shutil
import tempfile
from datetime import datetime

from console import error2


def has_subproject(project_path, name):
    """Return True when ``<project_path>/<name>/build.gradle.kts`` exists."""
    return os.path.exists(os.path.join(project_path, name, "build.gradle.kts"))


def copy_from_template(source_path, destination_path, only_if_absent=False, throw_when_not_found=True):
    """Copy a file or directory tree from a template into place.

    Files are copied with ``shutil.copy``. Directory sources are first copied
    into a temporary staging directory and then moved into place, so a failed
    copy cannot remove an existing destination. The copy is skipped when the
    source and destination resolve to the same file.

    Args:
        source_path: File or directory to copy from.
        destination_path: File or directory to copy to.
        only_if_absent: Skip the copy when ``destination_path`` already exists.
        throw_when_not_found: Call ``error2`` (which exits) when the source is
            missing; when False, ignore a missing source.

    Side effects: creates, replaces, or deletes files and directories and
    prints a progress line on success.
    """
    if only_if_absent and os.path.exists(destination_path):
        return

    if (
        os.path.exists(source_path)
        and os.path.exists(destination_path)
        and os.path.samefile(source_path, destination_path)
    ):
        return

    if os.path.isfile(source_path):
        shutil.copy(source_path, destination_path)

    elif os.path.isdir(source_path):
        parent_path = os.path.dirname(destination_path) or "."
        os.makedirs(parent_path, exist_ok=True)

        # Copy next to the destination first, so a failed copy cannot destroy
        # an existing destination directory.
        staged_path = tempfile.mkdtemp(prefix=".copy-", dir=parent_path)
        try:
            staged_copy = os.path.join(staged_path, "copy")
            shutil.copytree(source_path, staged_copy)

            if os.path.exists(destination_path):
                shutil.rmtree(destination_path)

            shutil.move(staged_copy, destination_path)
        finally:
            shutil.rmtree(staged_path, ignore_errors=True)

    elif throw_when_not_found:
        error2(f"Not found: {source_path}")

    else:
        return

    print(f"Copied {source_path} -> {destination_path}")


def move_directory_or_file(source_path, destination_path):
    """Move a file or directory when the source exists.

    Side effects: renames/moves the source path and prints a progress line;
    does nothing when the source does not exist.
    """
    if os.path.isdir(source_path) or os.path.isfile(source_path):
        shutil.move(source_path, destination_path)
        print(f"Moved {source_path} -> {destination_path}")


def remove_directory_or_file(file_path, only_if_empty=False):
    """Remove a file or directory tree.

    Args:
        file_path: Path to remove.
        only_if_empty: For directories, keep the directory when it contains
            entries.

    Side effects: deletes the path and prints a progress line; does nothing
    when the path does not exist.
    """
    if os.path.isdir(file_path):
        if only_if_empty and os.listdir(file_path):
            return
        shutil.rmtree(file_path)
    elif os.path.isfile(file_path):
        os.remove(file_path)
    else:
        return

    print(f"Removed {file_path}")


def string_in_file_if_exists(file_path, target):
    """Return True when ``target`` occurs in the UTF-8 text of ``file_path``.

    Returns False when the file does not exist.
    """
    if not os.path.isfile(file_path):
        return False
    with open(file_path, 'r', encoding='utf-8') as f:
        return target in f.read()


def replace_text_block(file_path, pattern, replacement, use_regex=True):
    """Replace ``pattern`` with ``replacement`` in a UTF-8 text file.

    Regex mode uses ``re.DOTALL | re.VERBOSE | re.MULTILINE``. The file is
    rewritten only when the text actually changes.

    Args:
        file_path: File to edit.
        pattern: Regex (default) or literal text to find.
        replacement: Replacement text.
        use_regex: When False, treat ``pattern`` as literal text.

    Side effects: writes the file on change and prints a progress line; does
    nothing when the file is missing.
    """
    if not os.path.exists(file_path):
        return

    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()

    if use_regex:
        new_text = re.sub(pattern, replacement, text, flags=re.DOTALL | re.VERBOSE | re.MULTILINE)
    else:
        new_text = text.replace(pattern, replacement)

    if text != new_text:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(new_text)

        print(f"Updated {file_path}")
    else:
        print(f"No change to {file_path}")


def update_license_year(file_path):
    """Bump the copyright year range on the first line of a license file.

    The first line must fullmatch
    ``Copyright (c) <year>[-<year>] @heyitsfuzs. All Rights Reserved.``.
    The end year is set to the current year; when the start year already is
    the current year, nothing changes. Only the first line is updated; all
    other lines are preserved.

    Args:
        file_path: License file whose first line is updated.

    Side effects: rewrites ``file_path`` and prints a progress line when the
    year changes.
    """
    current_year = datetime.now().year

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return

    line = lines[0].rstrip("\n")

    pattern = re.compile(
        r"(Copyright \(c\) )(\d{4})(?:-(\d{4}))?( @heyitsfuzs\. All Rights Reserved\.)"
    )

    match = pattern.fullmatch(line)
    if not match:
        return

    start, year_start, year_end, rest = match.groups()
    year_start = int(year_start)
    year_end = int(year_end) if year_end else None

    if year_end == current_year or year_start == current_year:
        return

    new_years = f"{year_start}-{current_year}" if year_start != current_year else str(current_year)
    lines[0] = f"{start}{new_years}{rest}\n"

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"Updated copyright year in {file_path}")
