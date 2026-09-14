#!/usr/bin/env python3
"""Changelog parsing, generation, and insertion.

Purpose: turn ``--changelog`` section/text pairs into a Keep-a-Changelog entry
and insert it at the top of a project's ``CHANGELOG.md``.

Entry points: ``main.py`` calls ``parse_changelog_sections``,
``generate_changelog_block``, and ``prepend_to_changelog``.

Side effects: reads and writes ``CHANGELOG.md``; exits via ``error2`` for an
unknown section or a duplicate version.

Constraints: standard library only. Sections render in the fixed
``ORDERED_CHANGELOG_SECTIONS`` order regardless of the order supplied.
"""

from collections import defaultdict
from datetime import date

from console import error2
from validation import is_valid_parameter


ORDERED_CHANGELOG_SECTIONS = ["added", "changed", "deprecated", "removed", "fixed", "security"]
VALID_CHANGELOG_SECTIONS = set(ORDERED_CHANGELOG_SECTIONS)


def parse_changelog_sections(section_pairs):
    """Group ``--changelog`` pairs by lowercased section name.

    Args:
        section_pairs: Iterable of ``(section, text)`` pairs.

    Returns:
        A ``{section: ["- text", ...]}`` dict, or an empty dict for no input.

    Side effects: exits via ``error2`` for a section outside
    ``VALID_CHANGELOG_SECTIONS``.
    """
    if not section_pairs:
        return dict()

    changelog_section_data = defaultdict(list)

    for raw_header, line in section_pairs:
        header = raw_header.strip().lower()
        is_valid_parameter(header, VALID_CHANGELOG_SECTIONS)
        changelog_section_data[header].append(f"- {line.strip()}")

    return changelog_section_data


def generate_changelog_block(full_version, changelog_section_data):
    """Render a dated changelog entry.

    Args:
        full_version: Version label such as ``v26.2.0-mc26.2.x``.
        changelog_section_data: Output of ``parse_changelog_sections``.

    Returns:
        A ``(full_entry, body)`` tuple; ``full_entry`` includes the
        ``## [<version>] - <date>`` header and ``body`` is the section text
        without it.
    """
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
    """Insert ``new_entry`` after the preamble of ``changelog_path``.

    Creates a Keep-a-Changelog header when the file is missing. Does nothing
    when the version and body are already present.

    Args:
        changelog_path: Changelog file to edit.
        new_entry: ``(full_entry, body)`` tuple from
            ``generate_changelog_block``.
        full_version: Version label used to detect duplicates.

    Side effects: writes ``changelog_path``; exits via ``error2`` when the
    version exists with a different body.
    """
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
