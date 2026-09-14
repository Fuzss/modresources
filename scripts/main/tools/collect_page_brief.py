#!/usr/bin/env python3
"""Build a normalized authoring brief for a mod's page text.

Purpose: gather everything the page writer needs from a mod's git checkout
(``gradle.properties``, ``metadata.json``, ``README.md``, ``CHANGELOG.md``,
``@Config`` descriptions, language files, source inventory, existing page text,
and the manual-asset inventory) into a single deterministic document, so the
writer never has to guess where a fact lives.

Entry points: run directly as
``python3 tools/collect_page_brief.py <mod> [options]``; not dispatched by
``main.py``.

Side effects: reads the mod checkout and the pages tree. Writes to ``--out``
when given, otherwise prints to standard output. Performs no git operations and
writes nothing under ``pages/data/``.

Constraints: standard library only. Adds ``<scripts/main>/../core`` to
``sys.path`` so it can import ``gradle_user_properties`` by bare name. The mods
root defaults to the ``fuzs.multiloader.project.mods`` Gradle property and the
pages root to ``<fuzs.multiloader.project.resources>/pages``, falling back to
this repository's own ``pages/`` directory. The branch directory must exist.

Usage:
    python3 tools/collect_page_brief.py eternal-nether
    python3 tools/collect_page_brief.py mutant-monsters --branch 26.2.x \
        --out pages/.authoring/mutant-monsters/brief.md
    python3 tools/collect_page_brief.py air-hop --json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))

from gradle_user_properties import load_gradle_properties


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BRANCH = "26.2.x"
MAX_CHANGELOG_RELEASES = 3
MAX_NOTABLE_CLASSES = 80
MAX_SOURCE_DIRS = 40


def parse_properties(path):
    """Parse a Gradle ``key=value`` properties file into a dict.

    Raises:
        FileNotFoundError: when ``path`` does not exist.

    Side effects: reads ``path``.
    """
    properties = {}

    with path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            properties[key.strip()] = value.strip()

    return properties


def load_json(path):
    """Return the parsed JSON at ``path``, or None when it is missing/invalid.

    Side effects: reads ``path``.
    """
    if not path.is_file():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def split_readme(text):
    """Split a README into its enforced top section and its extended body.

    Returns:
        A ``(top, body)`` tuple of strings; ``top`` is the first five lines.

    Side effects: none.
    """
    lines = text.splitlines()
    return "\n".join(lines[:5]).strip(), "\n".join(lines[5:]).strip()


def recent_changelog(text, releases=MAX_CHANGELOG_RELEASES):
    """Return the most recent Keep-a-Changelog release sections.

    Args:
        text: the full ``CHANGELOG.md`` contents.
        releases: maximum number of ``##`` release sections to keep.

    Returns:
        The selected release sections as markdown, or the trimmed input when no
        ``##`` headings are present.

    Side effects: none.
    """
    lines = text.splitlines()
    headings = [index for index, line in enumerate(lines) if line.startswith("## ")]

    if not headings:
        return text.strip()

    selected = headings[:releases]
    end = headings[releases] if len(headings) > releases else len(lines)
    return "\n".join(lines[selected[0]:end]).strip()


def _matching_paren(text, open_index):
    """Return the index just past the ``)`` matching ``text[open_index]``.

    String literals and escapes are skipped so parentheses inside descriptions
    do not end the scan early.

    Returns:
        The index after the matching close parenthesis, or ``len(text)`` when the
        parenthesis is never closed.

    Side effects: none.
    """
    depth = 0
    in_string = False
    escaped = False
    index = open_index

    while index < len(text):
        character = text[index]

        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1

            if depth == 0:
                return index + 1

        index += 1

    return len(text)


def _unescape_java_string(value):
    """Decode the escape sequences that appear in config description strings.

    Side effects: none.
    """
    return value.replace('\\"', '"').replace("\\\\", "\\").replace("\\n", " ")


def collect_config_descriptions(java_root):
    """Collect ``@Config(description = "...")`` strings from the source tree.

    Returns:
        A list of ``(relative path, description)`` pairs in file order.

    Side effects: reads every ``*.java`` file below ``java_root``.
    """
    descriptions = []

    if not java_root.is_dir():
        return descriptions

    for java_file in sorted(java_root.rglob("*.java")):
        text = java_file.read_text(encoding="utf-8", errors="replace")
        start = 0

        while True:
            annotation = text.find("@Config", start)

            if annotation == -1:
                break

            open_index = text.find("(", annotation)

            if open_index == -1:
                break

            end_index = _matching_paren(text, open_index)
            annotation_text = text[open_index:end_index]
            match = re.search(r'description\s*=\s*"((?:[^"\\]|\\.)*)"', annotation_text)

            if match:
                descriptions.append(
                    (str(java_file.relative_to(java_root)), _unescape_java_string(match.group(1)))
                )

            start = end_index

    return descriptions


def collect_language_entries(resources_root):
    """Merge every ``lang/en_us.json`` below ``resources_root`` into one dict.

    Returns:
        A ``{translation key: value}`` dict with later files overriding earlier
        ones.

    Side effects: reads all matching language files.
    """
    entries = {}

    if not resources_root.is_dir():
        return entries

    for lang_file in sorted(resources_root.rglob("lang/en_us.json")):
        data = load_json(lang_file)

        if isinstance(data, dict):
            entries.update(data)

    return entries


def collect_source_inventory(java_root):
    """Summarize the source tree as package file counts and notable class names.

    Returns:
        A ``(directory counts, notable classes)`` tuple. Directory counts map a
        relative directory to its number of ``*.java`` files. Notable classes are
        class names matching common feature-bearing suffixes, capped for size.

    Side effects: reads the source tree layout.
    """
    counts = {}
    notable = set()
    suffixes = ("Entity", "Block", "Item", "Handler", "Manager", "Registry", "Goal", "Renderer")

    if not java_root.is_dir():
        return counts, []

    for java_file in sorted(java_root.rglob("*.java")):
        relative = java_file.relative_to(java_root)
        directory = str(relative.parent)
        counts[directory] = counts.get(directory, 0) + 1

        stem = java_file.stem

        if stem not in {"ModRegistry", "ModConfig"} and stem.endswith(suffixes):
            notable.add(stem)

    trimmed = dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:MAX_SOURCE_DIRS])
    return trimmed, sorted(notable)[:MAX_NOTABLE_CLASSES]


def collect_manual_assets(data_dir):
    """Report which manual page files and assets are present for a mod.

    Returns:
        A list of ``(label, state)`` pairs, where ``state`` is ``present``,
        ``missing``, or a media file count.

    Side effects: reads the data directory listing.
    """
    results = []

    for name in ("banner.png", "logo.png", "strip.png", "installation.yaml", "sections.yaml",
                 "configuration.md", "credits.md", "socials.yaml"):
        path = data_dir / name
        results.append((name, "present" if path.is_file() else "missing"))

    media_dir = data_dir / "media"

    if media_dir.is_dir():
        media_files = sorted(path for path in media_dir.iterdir() if path.is_file())
        results.append(("media/", f"{len(media_files)} file(s)"))
    else:
        results.append(("media/", "missing"))

    return results


def resolve_mods_root(explicit):
    """Resolve the mods root from the argument or the Gradle user properties.

    Raises:
        SystemExit: when neither source provides a usable directory.

    Side effects: reads ``~/.gradle/gradle.properties`` and the filesystem.
    """
    if explicit:
        root = Path(explicit).expanduser()
    else:
        try:
            properties = load_gradle_properties()
        except FileNotFoundError:
            properties = {}

        configured = properties.get("fuzs.multiloader.project.mods")

        if not configured:
            sys.exit(
                "No mods root: pass --mods-root or set fuzs.multiloader.project.mods "
                "in ~/.gradle/gradle.properties"
            )

        root = Path(configured).expanduser()

    if not root.is_dir():
        sys.exit(f"Mods root does not exist: {root}")

    return root


def resolve_pages_root(explicit):
    """Resolve the pages root from the argument, Gradle properties, or this repo.

    Side effects: reads ``~/.gradle/gradle.properties`` and the filesystem.
    """
    if explicit:
        return Path(explicit).expanduser()

    try:
        properties = load_gradle_properties()
    except FileNotFoundError:
        properties = {}

    configured = properties.get("fuzs.multiloader.project.resources")

    if configured:
        return Path(configured).expanduser() / "pages"

    return REPO_ROOT / "pages"


def build_brief(mod, branch, mods_root, pages_root):
    """Build the complete brief data structure for one mod.

    Args:
        mod: mod repository directory name (hyphens included).
        branch: version branch directory name.
        mods_root: directory containing the mod checkouts.
        pages_root: the pages data root.

    Raises:
        SystemExit: when the mod or branch checkout does not exist.

    Returns:
        A dict with every collected section.

    Side effects: reads the mod checkout and the pages tree.
    """
    mod_dir = mods_root / mod

    if not mod_dir.is_dir():
        sys.exit(f"Mod repository does not exist: {mod_dir}")

    branch_dir = mod_dir / branch

    if not branch_dir.is_dir():
        branches = sorted(path.name for path in mod_dir.iterdir() if path.is_dir())
        sys.exit(f"Branch '{branch}' does not exist for {mod}. Available: {', '.join(branches)}")

    local_id = mod.replace("-", "")
    data_dir = pages_root / "data" / local_id
    properties = parse_properties(branch_dir / "gradle.properties")
    metadata = load_json(branch_dir / "metadata.json")
    readme_top, readme_body = ("", "")

    if (branch_dir / "README.md").is_file():
        readme_top, readme_body = split_readme(
            (branch_dir / "README.md").read_text(encoding="utf-8")
        )

    changelog = ""

    if (branch_dir / "CHANGELOG.md").is_file():
        changelog = recent_changelog(
            (branch_dir / "CHANGELOG.md").read_text(encoding="utf-8")
        )

    common_dir = branch_dir / "Common"
    config_descriptions = collect_config_descriptions(common_dir / "src/main/java")
    language_entries = collect_language_entries(common_dir / "src/generated/resources")
    source_dirs, notable_classes = collect_source_inventory(common_dir / "src/main/java")

    existing = {}

    for name in ("about.md", "features.md"):
        path = data_dir / name

        if path.is_file():
            existing[name] = path.read_text(encoding="utf-8").strip()

    dependencies = []

    for key, value in properties.items():
        if key.startswith("dependencies."):
            dependencies.append(f"{key[len('dependencies.'):]}={value}")

    environments = {
        key[len("environments."):]: value
        for key, value in properties.items()
        if key.startswith("environments.")
    }

    return {
        "mod": mod,
        "branch": branch,
        "local_id": local_id,
        "checkout": str(branch_dir),
        "data_dir": str(data_dir),
        "data_dir_exists": data_dir.is_dir(),
        "properties": {
            "name": properties.get("mod.name"),
            "id": properties.get("mod.id"),
            "description": properties.get("mod.description"),
            "authors": properties.get("mod.authors"),
            "license": properties.get("mod.license"),
            "version": properties.get("mod.version"),
            "platforms": properties.get("project.platforms"),
            "dependencies": sorted(dependencies),
            "environments": environments,
        },
        "metadata": metadata,
        "readme_top": readme_top,
        "readme_body": readme_body,
        "changelog": changelog,
        "config_descriptions": config_descriptions,
        "language_entries": language_entries,
        "source_dirs": source_dirs,
        "notable_classes": notable_classes,
        "existing_page": existing,
        "manual_assets": collect_manual_assets(data_dir),
    }


def render_markdown(brief):
    """Render a brief dict as the markdown document passed to the writer.

    Side effects: none.
    """
    lines = [f"# Authoring brief: {brief['properties'].get('name') or brief['mod']}", ""]
    lines.append(f"- Repository: {brief['mod']}")
    lines.append(f"- Checkout: {brief['checkout']}")
    lines.append(f"- Branch: {brief['branch']}")
    lines.append(f"- Local id: {brief['local_id']}")
    lines.append(f"- Data dir: {brief['data_dir']} (exists: {brief['data_dir_exists']})")
    lines.append(f"- Existing about.md: {'yes' if 'about.md' in brief['existing_page'] else 'no'}")
    lines.append(f"- Existing features.md: {'yes' if 'features.md' in brief['existing_page'] else 'no'}")
    lines.append("")

    lines.append("## gradle.properties")
    lines.append("")
    properties = brief["properties"]
    lines.append(f"- name: {properties.get('name')}")
    lines.append(f"- id: {properties.get('id')}")
    lines.append(f"- description: {properties.get('description')}")
    lines.append(f"- authors: {properties.get('authors')}")
    lines.append(f"- license: {properties.get('license')}")
    lines.append(f"- version: {properties.get('version')}")
    lines.append(f"- platforms: {properties.get('platforms')}")

    if properties.get("environments"):
        environments = ", ".join(
            f"{key}={value}" for key, value in properties["environments"].items()
        )
        lines.append(f"- environments: {environments}")

    if properties.get("dependencies"):
        lines.append("- dependencies:")

        for dependency in properties["dependencies"]:
            lines.append(f"  - {dependency}")

    lines.append("")

    if brief["metadata"] is not None:
        lines.append("## metadata.json")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(brief["metadata"], indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")

    lines.append("## Manual assets")
    lines.append("")

    for label, state in brief["manual_assets"]:
        lines.append(f"- {label}: {state}")

    lines.append("")
    lines.append("## README top section")
    lines.append("")
    lines.append(brief["readme_top"] or "(missing)")
    lines.append("")
    lines.append("## README extended body")
    lines.append("")
    lines.append(brief["readme_body"] or "(none)")
    lines.append("")
    lines.append("## Changelog (recent releases)")
    lines.append("")
    lines.append(brief["changelog"] or "(missing)")
    lines.append("")
    lines.append("## Configuration descriptions (`@Config`)")
    lines.append("")

    if brief["config_descriptions"]:
        for path, description in brief["config_descriptions"]:
            lines.append(f"- {description} ({path})")
    else:
        lines.append("(none found)")

    lines.append("")
    lines.append("## Language entries (`en_us.json`)")
    lines.append("")

    if brief["language_entries"]:
        for key, value in sorted(brief["language_entries"].items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("(none found)")

    lines.append("")
    lines.append("## Source inventory")
    lines.append("")

    if brief["source_dirs"]:
        for directory, count in brief["source_dirs"].items():
            lines.append(f"- {directory}: {count} file(s)")
    else:
        lines.append("(no Common sources found)")

    if brief["notable_classes"]:
        lines.append("")
        lines.append("Notable classes:")
        lines.append("")
        lines.append(", ".join(brief["notable_classes"]))

    lines.append("")
    lines.append("## Existing page text")
    lines.append("")

    for name in ("about.md", "features.md"):
        lines.append(f"### {name}")
        lines.append("")
        lines.append(brief["existing_page"].get(name, "(missing)"))
        lines.append("")

    return "\n".join(lines)


def parse_args():
    """Parse the command-line arguments.

    Side effects: reads ``sys.argv``.
    """
    parser = argparse.ArgumentParser(description="Build a mod page authoring brief.")
    parser.add_argument("mod", help="mod repository directory name, e.g. air-hop")
    parser.add_argument("--branch", default=DEFAULT_BRANCH, help=f"branch (default: {DEFAULT_BRANCH})")
    parser.add_argument("--mods-root", help="directory containing the mod checkouts")
    parser.add_argument("--pages-root", help="pages data root (default: this repo's pages/)")
    parser.add_argument("--out", help="write the brief to this file instead of stdout")
    parser.add_argument("--json", action="store_true", help="emit the raw brief as JSON")
    return parser.parse_args()


def main():
    """Build one mod's brief and print or write it.

    Side effects: see the module docstring.
    """
    args = parse_args()
    brief = build_brief(
        args.mod,
        args.branch,
        resolve_mods_root(args.mods_root),
        resolve_pages_root(args.pages_root),
    )
    output = json.dumps(brief, indent=2, ensure_ascii=False) if args.json else render_markdown(brief)

    if args.out:
        out_path = Path(args.out).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
