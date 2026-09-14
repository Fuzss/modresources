#!/usr/bin/env python3
"""Changelog parsing, generation, and insertion."""

from collections import defaultdict
from datetime import date

from console import error2
from validation import is_valid_parameter


ORDERED_CHANGELOG_SECTIONS = ["added", "changed", "deprecated", "removed", "fixed", "security"]
VALID_CHANGELOG_SECTIONS = set(ORDERED_CHANGELOG_SECTIONS)


def parse_changelog_sections(section_pairs):
    if not section_pairs:
        return dict()

    changelog_section_data = defaultdict(list)

    for raw_header, line in section_pairs:
        header = raw_header.strip().lower()
        is_valid_parameter(header, VALID_CHANGELOG_SECTIONS)
        changelog_section_data[header].append(f"- {line.strip()}")

    return changelog_section_data


def generate_changelog_block(full_version, changelog_section_data):
    today = date.today().isoformat()
    header = f"## [{full_version}] - {today}"
    body = []

    for section in ORDERED_CHANGELOG_SECTIONS:
        if section in changelog_section_data:
            body.append(f"### {section.capitalize()}")
            body.append("")
            body.extend(changelog_section_data[section])
            body.append("")

    full_body = "\n".join(body).rstrip()
    return (header + "\n\n" + full_body + "\n", full_body)


def prepend_to_changelog(changelog_path, new_entry, full_version):
    try:
        with open(changelog_path, encoding="utf-8") as f:
            existing = f.read()
    except FileNotFoundError:
        existing = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
        """

    if full_version in existing:
        if new_entry[1] in existing:
            return
        else:
            error2(f"Duplicate changelog version: {full_version}")

    if "## [" in existing:
        preamble, rest = existing.split("## [", 1)
        updated = preamble.rstrip() + "\n\n" + new_entry[0] + "\n## [" + rest
    else:
        updated = existing.rstrip() + "\n\n" + new_entry[0]

    with open(changelog_path, "w", encoding="utf-8") as f:
        f.write(updated)
