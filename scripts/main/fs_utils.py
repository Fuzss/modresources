#!/usr/bin/env python3
"""Filesystem, string, and license helpers shared by the modding scripts."""

import os
import re
import shutil
import tempfile
from datetime import datetime

from console import error2


def has_subproject(project_path, name):
    return os.path.exists(os.path.join(project_path, name, "build.gradle.kts"))


def copy_from_template(source_path, destination_path, only_if_absent=False, throw_when_not_found=True):
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
    if os.path.isdir(source_path) or os.path.isfile(source_path):
        shutil.move(source_path, destination_path)
        print(f"Moved {source_path} -> {destination_path}")


def remove_directory_or_file(file_path, only_if_empty=False):
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
    if not os.path.isfile(file_path):
        return False
    with open(file_path, 'r', encoding='utf-8') as f:
        return target in f.read()


def replace_text_block(file_path, pattern, replacement, use_regex=True):
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
    current_year = datetime.now().year

    with open(file_path, "r", encoding="utf-8") as f:
        line = f.readline().rstrip("\n")

    # Match line with the specific holder
    pattern = re.compile(
        r"(Copyright \(c\) )(\d{4})(?:-(\d{4}))?( @heyitsfuzs\. All Rights Reserved\.)"
    )

    match = pattern.fullmatch(line)
    if not match:
        return

    start, year_start, year_end, rest = match.groups()
    year_start = int(year_start)
    year_end = int(year_end) if year_end else None

    # Check if current year is already included
    if year_end == current_year or year_start == current_year:
        return

    # Build new year string
    new_years = f"{year_start}-{current_year}" if year_start != current_year else str(current_year)
    new_line = f"{start}{new_years}{rest}\n"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_line)

    print(f"Updated copyright year in {file_path}")
