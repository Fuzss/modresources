#!/usr/bin/env python3
import xml.etree.ElementTree as ET
from pathlib import Path

maven_root = Path("./maven")
readme_filename = "README.md"

def parse_metadata_files(root: Path):
    """Return dict: group_path -> {artifact_id -> [versions]}"""
    metadata_files = sorted(root.rglob("maven-metadata.xml"))
    groups = {}
    for meta_file in metadata_files:
        artifact_dir = meta_file.parent
        artifact_id = artifact_dir.name
        group_path = artifact_dir.parent.relative_to(root)

        tree = ET.parse(meta_file)
        versions_el = tree.find("versioning/versions")
        versions = [v.text for v in versions_el.findall("version")] if versions_el is not None else []

        groups.setdefault(group_path, {})[artifact_id] = versions
    return groups

def generate_artifacts_block(group_path, artifacts, header_level=2, details_open=False, relative_links=True):
    """Generate Markdown block for a group, including the group header and artifacts."""
    lines = [f"{'#' * header_level} `{group_path}`\n"]  # top-level header for group
    lines.append(f"<details{' open' if details_open else ''}>")
    lines.append("<summary>Artifacts</summary>\n")
    for artifact_id in sorted(artifacts.keys()):
        versions = artifacts[artifact_id]
        lines.append(f"{'#' * (header_level + 1)} `{artifact_id}`")
        lines.append(f"<details{' open' if details_open else ''}>")
        lines.append("<summary>Versions</summary>\n")
        for version in versions:
            link_path = f"{artifact_id}/{version}" if relative_links else f"{group_path}/{artifact_id}/{version}"
            lines.append(f"- [{version}]({link_path})")
        lines.append("</details>\n")
    lines.append("</details>\n")
    return lines

def write_group_readmes(groups):
    for group_path, artifacts in groups.items():
        group_dir = maven_root / group_path
        group_dir.mkdir(parents=True, exist_ok=True)

        lines = generate_artifacts_block(group_path, artifacts, header_level=2, details_open=True, relative_links=True)

        readme_file = group_dir / readme_filename
        readme_file.write_text("\n".join(lines))
        print(f"Wrote {readme_file}")

def write_root_readme(groups):
    lines = ["# Maven Repository Index\n"]  # top-level header
    for group_path, artifacts in sorted(groups.items()):
        block = generate_artifacts_block(group_path, artifacts, header_level=2, details_open=False, relative_links=False)
        lines.extend(block)

    root_file = maven_root / readme_filename
    root_file.write_text("\n".join(lines))
    print(f"Wrote {root_file}")

if __name__ == "__main__":
    groups = parse_metadata_files(maven_root)
    write_group_readmes(groups)
    write_root_readme(groups)
