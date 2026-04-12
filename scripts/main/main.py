#!/usr/bin/env python3
import shutil
import sys
import os
import subprocess
import argparse
import re
import json
import clone_versions
import migrate_mod_properties
import migrate_mixins
from collections import defaultdict
from datetime import date
from datetime import datetime

_GRADLE_PROPS = None
ORDERED_CHANGELOG_SECTIONS = ["added", "changed", "deprecated", "removed", "fixed", "security"]
VALID_CHANGELOG_SECTIONS = set(ORDERED_CHANGELOG_SECTIONS)
ENVIRONMENTS = {"finder", "idea"}
MOD_LOADERS = {"fabric", "neoforge"}
DISTRIBUTIONS = {"client", "server"}
UPLOADING_SITES = {"curseforge", "modrinth", "github"}

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--branch", default=[], action="append", nargs=2, metavar=("BRANCH_NAME", "SUPPORT_STATUS"), help="Updates branch status in versions.json, can be used multiple times. Format: --branch <branch_name> <support_status>")
    parser.add_argument('--catalog', type=str, default=None, metavar="VERSION_CATALOG", help="Version-based catalog. Example: --catalog 26.1-SNAPSHOT")
    parser.add_argument("--changelog", default=None, action="append", nargs=2, metavar=("SECTION_NAME", "TEXT"), help="Add a changelog line, can be used multiple times. Format: --changelog <section_name> <text>")
    parser.add_argument('--commit', default=False, action="store_true", help="Commit to GitHub.")
    parser.add_argument('--data', default=False, action="store_true", help="Generate data.")
    parser.add_argument('--gradle', type=str, default=None, metavar="GRADLE_VERSION", help="Gradle wrapper version. Example: --gradle 9.4.1")
    parser.add_argument('--id', type=str, default=None, metavar="MOD_ID", help="Mod id. Example: --id examplemod")
    parser.add_argument('--init', nargs='?', const=True, default=None, metavar="SOURCE_BRANCH", help="Setup git repository and version branch, with optional argument. Example: --init [1.21.11]")
    parser.add_argument('--launch', default=[], action="append", nargs="*", metavar=("MOD_LOADER", "DISTRIBUTION"), help="Launch the game, can be used multiple times. Format: --launch <mod_loader> <distribution>")
    parser.add_argument('--legacy', default=False, action="store_true", help="Use legacy Gradle task names.")
    parser.add_argument('--minecraft', type=str, required=True, metavar="MINECRAFT_VERSION", help="Minecraft name. Example: --minecraft 26.1.x")
    parser.add_argument('--name', type=str, required=True, metavar="REPOSITORY_NAME", help="Repository name. Example: --name example-mod")
    parser.add_argument('--notify', default=False, action="store_true", help="Notify via Discord webhook.")
    parser.add_argument('--open', default=None, nargs="*", metavar="ENVIRONMENT", help="Open in Finder, or Idea. Format: --open <environment>")
    parser.add_argument('--path', type=str, default=None, metavar="ROOT_PATH", help="Override default root path. Example: --path /absolute/path/to/project")
    parser.add_argument("--properties", default=None, action="append", nargs=2, metavar=("KEY", "VALUE"), help="Set a gradle.properties value, can be used multiple times. Format: --properties <key> <value>")
    parser.add_argument('--publish', default=False, action="store_true", help="Publish to Maven.")
    parser.add_argument('--sources', default=False, action="store_true", help="Generate common sources.")
    parser.add_argument('--upgrade', nargs='?', const=True, default=None, metavar="PATCHES_NAME", help="Run workspace upgrade, potentially for a specific version, with optional argument. Example: --upgrade [1.21.11]")
    parser.add_argument('--upload', default=None, nargs="*", metavar=("MOD_LOADER", "WEBSITE"), help="Upload to CurseForge, Modrinth, or GitHub. Format: --upload <mod_loader> <website>")
    parser.add_argument('--version', type=str, default=None, metavar="PROJECT_VERSION", help="Mod version. Example: --version 21.8.0")

    args = parser.parse_args()

    if not args.id:
        args.id = args.name.replace("-", "")
    
    if isinstance(args.init, str):
        if not any(version == args.minecraft for version, _ in args.branch):
            args.branch.append((args.minecraft, "primary"))

        if not any(version == args.init for version, _ in args.branch):
            args.branch.append((args.init, ""))

        if not args.data:
            args.data = True

        if not args.upgrade:
            args.upgrade = args.minecraft

        if not args.changelog:
            args.changelog = [["changed", f"Update to Minecraft {args.minecraft}"]]

    return args

def log2(level, color, message):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"\033[1;{color}m[{now}] [{level}] {message}\033[0m")

def info2(message):
    log2("INFO", "36", message)   # cyan

def warn2(message):
    log2("WARN", "33", message)   # yellow

def error2(message):
    log2("ERROR", "31", message)   # red
    sys.exit(1)

def copy_from_template(source_path, destination_path, only_if_absent=False):
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
        if os.path.exists(destination_path):
            shutil.rmtree(destination_path)

        shutil.copytree(source_path, destination_path)

    else:
        error2(f"Not found: {source_path}")

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

def update_gradle_properties(file_path, updates: dict):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    new_lines = []

    for line in lines:
        content = line.strip()
        if not content or '=' not in line:
            new_lines.append(line)
            continue

        prefix = ""
        if content.startswith('#'):
            content = content[1:].strip()
            prefix = "#"

        key, _ = content.split('=', 1)
        key = key.strip()
        if key in updates:
            new_value = updates[key]
            if new_value == "#":
                new_lines.append(f"#{line}")
            elif new_value is not None:
                new_lines.append(f"{prefix}{key}={new_value}\n")
        else:
            new_lines.append(line)

    with open(file_path, 'w') as f:
        f.writelines(new_lines)

def load_gradle_properties():
    path = os.path.expanduser("~/.gradle/gradle.properties")
    props = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                props[key.strip()] = value.strip()

    return props

def find_gradle_property(prop, default=None):
    global _GRADLE_PROPS
    if _GRADLE_PROPS is None:
        _GRADLE_PROPS = load_gradle_properties()
    if prop in _GRADLE_PROPS:
        return _GRADLE_PROPS[prop]
    elif default is not None:
        return default
    else:
        error2(f"Missing property {prop} in ~/.gradle/gradle.properties")

def get_remote_url(args):
    token = find_gradle_property("fuzs.multiloader.project.github.token")
    return f"https://{token}@github.com/Fuzss/{args.name}.git"

def git_push_all(args, repo_path, commit_message):
    remote_url = get_remote_url(args)

    subprocess.run(
        ["git", "remote", "set-url", "origin", remote_url], 
        cwd=repo_path, 
        check=True
    )

    subprocess.run(
        ["git", "add", "."], 
        cwd=repo_path, 
        check=True
    )

    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo_path
    )

    if result.returncode == 0:
        print("No changes to commit, skipping commit and push.")
        return False
    
    subprocess.run(
        ["git", "commit", "-m", commit_message],
        cwd=repo_path,
        check=True
    )

    subprocess.run(
        ["git", "push"],
        cwd=repo_path,
        check=True
    )

    return True

def is_valid_parameter(value, allowed_values):
    if value not in allowed_values:
        error2(f"Invalid parameter '{value}'. Must be one of: {', '.join(allowed_values)}")

def validate_open_parameters(parameters, fallback_parameter):
    if parameters is None:
        return None
    elif len(parameters) == 0:
        return fallback_parameter
    
    environment = parameters[0].lower()
    is_valid_parameter(environment, ENVIRONMENTS)
    return environment

def validate_launch_parameters(parameters, fallback_parameters):
    if parameters is None:
        return None
    elif len(parameters) == 0:
        parameters = fallback_parameters
    elif len(parameters) == 1:
        parameters = (parameters[0], fallback_parameters[1])

    mod_loader = parameters[0].lower()
    other_argument = parameters[1].lower()
    is_valid_parameter(mod_loader, MOD_LOADERS)
    is_valid_parameter(other_argument, DISTRIBUTIONS)
    return (mod_loader, other_argument)

def validate_upload_parameters(parameters):
    if parameters is None:
        return None
    elif len(parameters) == 0:
        return (None, None)
    elif len(parameters) == 1:
        parameter = parameters[0].lower()
        if parameter in MOD_LOADERS:
            return (parameter, None)
        elif parameter in UPLOADING_SITES:
            return (None, parameter)

    mod_loader = parameters[0].lower()
    other_argument = parameters[1].lower()
    is_valid_parameter(mod_loader, MOD_LOADERS)
    is_valid_parameter(other_argument, UPLOADING_SITES)
    return (mod_loader, other_argument)

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

    return header + "\n\n" + "\n".join(body).rstrip() + "\n"

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
        error2(f"Duplicate changelog version: {full_version}")

    if "## [" in existing:
        preamble, rest = existing.split("## [", 1)
        updated = preamble.rstrip() + "\n\n" + new_entry + "\n## [" + rest
    else:
        updated = existing.rstrip() + "\n\n" + new_entry

    with open(changelog_path, "w", encoding="utf-8") as f:
        f.write(updated)

def string_in_file_if_exists(file_path, target):
    if not os.path.isfile(file_path):
        return False
    with open(file_path, 'r', encoding='utf-8') as f:
        return target in f.read()

def create_gradle_properties(args):
    if args.upgrade == "1.21.10":
        gradle_properties = {
            "dependenciesPuzzlesLibVersion": None,
            "dependenciesMinPuzzlesLibVersion": None,
            "dependenciesRequiredForgeCurseForge": None,
            "dependenciesRequiredForgeModrinth": None,
            "dependenciesOptionalFabricCurseForge": None,
            "dependenciesOptionalNeoForgeCurseForge": None,
            "dependenciesOptionalForgeCurseForge": None,
            "dependenciesOptionalFabricModrinth": None,
            "dependenciesOptionalNeoForgeModrinth": None,
            "dependenciesOptionalForgeModrinth": None
        }
    else:
        gradle_properties = {}

    if args.version:
        gradle_properties["modVersion" if args.legacy else "mod.version"] = args.version

    if args.catalog:
        gradle_properties["dependenciesVersionCatalog" if args.legacy else "project.libs"] = args.catalog

    if args.properties:
        for key, value in args.properties:
            gradle_properties[key.strip()] = value.strip()

    return gradle_properties

def run_launch(mod_loader, distribution, project_path, legacy_task_names=False):
    if mod_loader == "fabric":
        if distribution == "client":
            subprocess.run(["./gradlew", "fabricClient" if legacy_task_names else "fabric-client"], cwd=project_path, check=True)
        elif distribution == "server":
            subprocess.run(["./gradlew", "fabricServer" if legacy_task_names else "fabric-server"], cwd=project_path, check=True)
        else:
            error2(f"Unsupported argument: {distribution}")
    elif mod_loader == "neoforge":
        if distribution == "client":
            subprocess.run(["./gradlew", "neoForgeClient" if legacy_task_names else "neoforge-client"], cwd=project_path, check=True)
        elif distribution == "server":
            subprocess.run(["./gradlew", "neoForgeServer" if legacy_task_names else "neoforge-server"], cwd=project_path, check=True)
        else:
            error2(f"Unsupported argument: {distribution}")
    else:
        error2(f"Unsupported argument: {mod_loader}")

def run_upload(mod_loader, website, project_path, legacy_task_names=False):
    if mod_loader == "fabric":
        if website == "curseforge":
            subprocess.run(["./gradlew", "fabricUploadCurseForge" if legacy_task_names else "fabric-curseforge"], cwd=project_path, check=True)
        elif website == "modrinth":
            subprocess.run(["./gradlew", "fabricUploadModrinth" if legacy_task_names else "fabric-modrinth"], cwd=project_path, check=True)
        elif website == "github":
            subprocess.run(["./gradlew", "fabricUploadGitHub" if legacy_task_names else "fabric-github"], cwd=project_path, check=True)
        else:
            subprocess.run(["./gradlew", "fabricUploadEverywhere" if legacy_task_names else "fabric-all"], cwd=project_path, check=True)
    elif mod_loader == "neoforge":
        if website == "curseforge":
            subprocess.run(["./gradlew", "neoForgeUploadCurseForge" if legacy_task_names else "neoforge-curseforge"], cwd=project_path, check=True)
        elif website == "modrinth":
            subprocess.run(["./gradlew", "neoForgeUploadModrinth" if legacy_task_names else "neoforge-modrinth"], cwd=project_path, check=True)
        elif website == "github":
            subprocess.run(["./gradlew", "neoForgeUploadGitHub" if legacy_task_names else "neoforge-github"], cwd=project_path, check=True)
        else:
            subprocess.run(["./gradlew", "neoForgeUploadEverywhere" if legacy_task_names else "neoforge-all"], cwd=project_path, check=True)
    else:
        if website == "curseforge":
            subprocess.run(["./gradlew", "allUploadCurseForge" if legacy_task_names else "all-curseforge"], cwd=project_path, check=True)
        elif website == "modrinth":
            subprocess.run(["./gradlew", "allUploadModrinth" if legacy_task_names else "all-modrinth"], cwd=project_path, check=True)
        elif website == "github":
            subprocess.run(["./gradlew", "allUploadGitHub" if legacy_task_names else "all-github"], cwd=project_path, check=True)
        else:
            subprocess.run(["./gradlew", "allUploadEverywhere" if legacy_task_names else "all-all"], cwd=project_path, check=True)

def update_json_object(edits: dict):
    def _update_json_object(match):
        prefix, block = match.groups()
        obj = json.loads(block)

        # Apply edits
        for key, value in edits.items():
            if value is None:
                obj.pop(key, None)
            else:
                obj[key] = value

        # Rebuild with preserved order
        formatted = json.dumps(obj, indent=2)

        # Determine base indentation from the block in the file
        base_indent = re.match(r'^\s*', block).group(0)
        inner_indent = base_indent + "  "  # 2 spaces more for inner keys

        # Add correct indentation to each line
        lines = formatted.splitlines()
        formatted = "\n".join([base_indent + lines[0]] +
                              [inner_indent + line for line in lines[1:-1]] +
                              [inner_indent + lines[-1]])

        return prefix + formatted
    return _update_json_object

def update_json_file(file_path, edits: dict, json_object_name):
    if not os.path.isfile(file_path):
        return
    
    json_object_pattern = re.compile(rf'("{json_object_name}"\s*:\s*)(\{{.*?\}})(?=[,\n])', re.DOTALL)

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    new_text = json_object_pattern.sub(update_json_object(edits), text, count=1)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_text)

    print(f"Updated {file_path}")

def add_simple_json_field(json_file, key, value):
    if not os.path.isfile(json_file):
        return
    
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if key in data:
        return
    
    data[key] = value

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Added {key}: {value} to {json_file}")

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

def update_toml_file(file_path, updates: dict):
    if not os.path.isfile(file_path):
        return
    
    # Update key-value pairs
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    text = ""
    inside_minecraft_block = False
    block_header = re.compile(r'^\s*\[{1,2}[^\]]+\]{1,2}\s*$')
    replaced_counts = {k: 0 for k, v in updates.items() if v is not None}

    for line in lines:
        # Reset context when a block header is found
        if block_header.match(line.strip()):
            inside_minecraft_block = False

        if '=' in line:
            key, value = map(str.strip, line.split('=', 1))

            if key == "modId" and value == '"minecraft"':
                inside_minecraft_block = True
            
            if key in updates:
                if key == "versionRange" and not inside_minecraft_block:
                    pass  # only update versionRange in minecraft block
                else:
                    value = updates[key]

                    if value is None:
                        continue  # remove line
                    else:
                        replaced_counts[key] += 1

            line = f"{key} = {value}\n"

        text += line

    # Remove empty blocks
    text = re.sub(
        r'^\s*\[{1,2}[^\]]+\]\s*\n(?=\n|\[{1,2}[^\]]+\]|\Z)',
        '',
        text,
        flags=re.MULTILINE,
    )

    # Remove duplicate blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Updated {file_path}")

def prepare_new_version(args, root_path, project_path):
    remote_url = get_remote_url(args)
    new_branch = args.minecraft
    source_branch = args.init

    if os.path.isdir(project_path):
        error2(f"Failed to create new branch {new_branch}: directory already exists")

    # check if remote branch exists
    result = subprocess.run(
        ["git", "ls-remote", "--heads", remote_url, new_branch],
        capture_output=True,
        text=True,
        check=True
    )

    if bool(result.stdout.strip()):
        error2(f"Failed to create new branch {new_branch}: branch already exists")

    # clone default then create branch
    subprocess.run(
        ["git", "clone", remote_url, new_branch],
        cwd=root_path,
        check=True
    )

    subprocess.run(
        ["git", "checkout", "-B", new_branch, f"origin/{source_branch}"],
        cwd=project_path,
        check=True
    )

    subprocess.run(
        ["git", "push", "-u", "origin", new_branch],
        cwd=project_path,
        check=True
    )
    
    print(f"Created new branch {new_branch} from {source_branch}")

    remove_directory_or_file(f"{project_path}/.idea")
    remove_directory_or_file(f"{project_path}/.gradle")
    remove_directory_or_file(f"{project_path}/CHANGELOG.md")

    if args.commit:
        if git_push_all(args, project_path, f"prepare {args.minecraft} port"):
            print("Committed new version preparations")

def replace_text_block(file_path, pattern, replacement, use_regex=True):
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

def add_line_after_target(file_path, target_text, new_text):
    """
    Adds new_text after the first occurrence of target_text in gradle_file,
    matching indentation. Does nothing if new_text already exists.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Check if the line already exists anywhere (ignoring leading/trailing whitespace)
    if any(line.strip() == new_text.strip() for line in lines):
        return  # Already present, nothing to do

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == new_text:
            # already present, nothing to do
            return
        if stripped == target_text:
            indent = line[:line.index(stripped)]
            lines.insert(i + 1, f"{indent}{new_text}\n")
            break

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"Updated {file_path}")

def run_26_1_upgrade(args, template_path, project_path):
    move_directory_or_file(
        os.path.join(project_path, "Common", "src", "main", "resources", "mod_logo.png"),
        os.path.join(project_path, "Common", "src", "main", "resources", "pack.png")
    )

    move_directory_or_file(
        os.path.join(project_path, "Common", "src", "main", "resources", f"{args.id}.accesswidener"),
        os.path.join(project_path, "Common", "src", "main", "resources", f"{args.id}.classtweaker")
    )

    replace_text_block(
        os.path.join(project_path, "Common", "src", "main", "resources", f"{args.id}.classtweaker"),
        "^accessWidener\s+v[12]\s+\w+\s*$",
        "classTweaker    v1  official"
    )

    replace_text_block(
        os.path.join(project_path, "Common", "build.gradle.kts"),
        "(libs.",
        "(sharedLibs.",
        use_regex=False
    )

    replace_text_block(
        os.path.join(project_path, "Fabric", "build.gradle.kts"),
        "(libs.",
        "(sharedLibs.",
        use_regex=False
    )

    replace_text_block(
        os.path.join(project_path, "NeoForge", "build.gradle.kts"),
        "(libs.",
        "(sharedLibs.",
        use_regex=False
    )

def run_1_21_11_upgrade(args, template_path, project_path):
    copy_from_template(f"{template_path}/settings.gradle.kts", f"{project_path}/settings.gradle.kts")
    copy_from_template(f"{template_path}/build.gradle.kts", f"{project_path}/build.gradle.kts")
    copy_from_template(f"{template_path}/Common/build.gradle.kts", f"{project_path}/Common/build.gradle.kts", only_if_absent=True)
    copy_from_template(f"{template_path}/Common/gradle.properties", f"{project_path}/Common/gradle.properties")
    copy_from_template(f"{template_path}/Fabric/build.gradle.kts", f"{project_path}/Fabric/build.gradle.kts", only_if_absent=True)
    copy_from_template(f"{template_path}/Fabric/gradle.properties", f"{project_path}/Fabric/gradle.properties")
    copy_from_template(f"{template_path}/NeoForge/build.gradle.kts", f"{project_path}/NeoForge/build.gradle.kts", only_if_absent=True)
    copy_from_template(f"{template_path}/NeoForge/gradle.properties", f"{project_path}/NeoForge/gradle.properties")

    migrate_mixins.convert_mixins(f"{project_path}/Common/src/main/resources/common.mixins.json", f"{project_path}/Common/build.gradle.kts")
    migrate_mixins.convert_mixins(f"{project_path}/Fabric/src/main/resources/fabric.mixins.json", f"{project_path}/Fabric/build.gradle.kts")
    migrate_mixins.convert_mixins(f"{project_path}/NeoForge/src/main/resources/neoforge.mixins.json", f"{project_path}/NeoForge/build.gradle.kts")
    migrate_mod_properties.migrate_properties(f"{project_path}/gradle.properties", f"{project_path}/gradle.properties")

    remove_directory_or_file(f"{project_path}/settings.gradle")
    remove_directory_or_file(f"{project_path}/build.gradle")
    remove_directory_or_file(f"{project_path}/Common/build.gradle")
    remove_directory_or_file(f"{project_path}/Common/src/main/resources/architectury.common.json")
    remove_directory_or_file(f"{project_path}/Common/src/main/resources/common.mixins.json")
    remove_directory_or_file(f"{project_path}/Common/src/main/resources/{args.id}.common.mixins.json")
    remove_directory_or_file(f"{project_path}/Fabric/build.gradle")
    remove_directory_or_file(f"{project_path}/Fabric/src/main/resources/fabric.mod.json")
    remove_directory_or_file(f"{project_path}/Fabric/src/main/resources/fabric.mixins.json")
    remove_directory_or_file(f"{project_path}/Fabric/src/main/resources/{args.id}.fabric.mixins.json")
    remove_directory_or_file(f"{project_path}/NeoForge/build.gradle")
    remove_directory_or_file(f"{project_path}/NeoForge/src/main/resources/META-INF/neoforge.mods.toml")
    remove_directory_or_file(f"{project_path}/NeoForge/src/main/resources/META-INF", only_if_empty=True)
    remove_directory_or_file(f"{project_path}/NeoForge/src/main/resources/neoforge.mixins.json")
    remove_directory_or_file(f"{project_path}/NeoForge/src/main/resources/{args.id}.neoforge.mixins.json")

def run_1_21_10_upgrade(args, template_path, project_path):
    move_directory_or_file(f"{project_path}/Common/src/main/resources/{args.id}.common.mixins.json", f"{project_path}/Common/src/main/resources/common.mixins.json")
    move_directory_or_file(f"{project_path}/Fabric/src/main/resources/{args.id}.fabric.mixins.json", f"{project_path}/Fabric/src/main/resources/fabric.mixins.json")
    move_directory_or_file(f"{project_path}/NeoForge/src/main/resources/{args.id}.neoforge.mixins.json", f"{project_path}/NeoForge/src/main/resources/neoforge.mixins.json")
    add_simple_json_field(f"{project_path}/Fabric/src/main/resources/fabric.mixins.json", "refmap", "${modId}.fabric.refmap.json")

    update_json_file(f"{project_path}/Fabric/src/main/resources/fabric.mod.json", {
        "java": None,
        "minecraft": ">=${minecraftVersion}- <${upcomingMinecraftVersion}-"
    }, "depends")

    update_toml_file(f"{project_path}/NeoForge/src/main/resources/META-INF/neoforge.mods.toml", {
        "logoFile": '"mod_logo.png"',
        "versionRange": '"[${minecraftVersion},${upcomingMinecraftVersion})"',
        "catalogueImageIcon": None
    })

    replace_text_block(
        f"{project_path}/Common/build.gradle", 
        r"""
^[ \t]*tasks\.withType\(net\.fabricmc\.loom\.task\.AbstractRemapJarTask\)\.configureEach\s*\{
[^}]*?
\}[ \t]*\n?
""", "")
    replace_text_block(
        f"{project_path}/settings.gradle", 
        "https://raw.githubusercontent.com/Fuzss/modresources/main/gradle/v2/settings.gradle", 
        "https://raw.githubusercontent.com/Fuzss/modresources/main/gradle/v3/settings.gradle", 
        False
    )
    
    add_line_after_target(
        f"{project_path}/build.gradle", 
        "alias libs.plugins.minotaur apply false", 
        "alias libs.plugins.modpublishplugin apply false"
    )

def run_workspace_upgrade(args, base_path, main_path, project_path):
    template_root_path = os.path.join(base_path, "mods", "multiloader-workspace-template")
    template_main_path = os.path.join(template_root_path, "main")
    template_project_path = os.path.join(template_root_path, args.minecraft)

    copy_from_template(
        os.path.join(template_main_path, ".gitignore"),
        os.path.join(main_path, ".gitignore"),
    )

    copy_from_template(
        os.path.join(template_main_path, ".github"),
        os.path.join(main_path, ".github"),
    )

    update_license_year(
        os.path.join(main_path, "LICENSE-ASSETS.md")
    )

    if args.commit and git_push_all(args, main_path, f"upgrade {args.minecraft} workspace"):
        print(f"Committed workspace upgrades on main")
    
    remove_directory_or_file(
        os.path.join(project_path, "Common", "src", "main", "resources", "pack.mcmeta")
    )

    remove_directory_or_file(
        os.path.join(project_path, "Common", "src", "main", "resources", "mod_banner.png")
    )

    if isinstance(args.upgrade, str):
        print(f"Running {args.upgrade} workspace upgrades")
        if args.upgrade == "26.1.x":
            run_26_1_upgrade(args, f"{template_project_path}", project_path)
        elif args.upgrade == "1.21.11":
            run_1_21_11_upgrade(args, f"{template_project_path}", project_path)
        elif args.upgrade == "1.21.10":
            run_1_21_10_upgrade(args, f"{template_project_path}", project_path)

    if args.commit and git_push_all(args, project_path, f"upgrade {args.minecraft} workspace"):
        print(f"Committed workspace upgrades on {args.minecraft}")

def main():
    args = parse_args()
    base_path = find_gradle_property("fuzs.multiloader.project.root")
    root_path = args.path or os.path.join(base_path, "mods", args.name)
    main_path = os.path.join(root_path, "main")
    project_path = os.path.join(root_path, args.minecraft)
    environment = validate_open_parameters(args.open, "finder")
    changelog_section_data = parse_changelog_sections(args.changelog)
    launch_parameters = [ 
        validate_launch_parameters(launch, ("fabric", "client")) 
        for launch in args.launch 
    ]
    upload_parameters = validate_upload_parameters(args.upload)

    if args.init:
        info2(f"Running init at {root_path}...")
        clone_versions.setup_git(root_path, args.name)

        if args.version and args.catalog and isinstance(args.init, str):
            info2(f"Preparing Minecraft version {args.minecraft}...")
            prepare_new_version(args, root_path, project_path)

    if not os.path.isdir(project_path):
        error2(f"Directory not found: {project_path}")

    if environment:
        info2(f"Opening in {environment.capitalize()}...")
        if environment == "finder":
            subprocess.Popen(["open", project_path], cwd=project_path)
        elif environment == "idea":
            try:
                subprocess.Popen(
                    ["open", "-a", "IntelliJ IDEA", project_path],
                    cwd=project_path,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except FileNotFoundError as e:
                warn2("Could not launch IntelliJ:", e)
        sys.exit(1)

    if args.branch:
        info2(f"Updating versions.json...")
        branch_overrides = {
            key.strip(): value.strip()
            for key, value in args.branch
        }
        clone_versions.load_versions_file(main_path, branch_overrides)

    if args.upgrade:
        info2("Upgrading workspace...")
        run_workspace_upgrade(args, base_path, main_path, project_path)

    if args.version:
        changelog_path = f"{project_path}/CHANGELOG.md"
        full_version = f"v{args.version}-mc{args.minecraft}"

        if changelog_section_data:
            info2(f"Updating CHANGELOG.md...")
            new_block = generate_changelog_block(full_version, changelog_section_data)
            prepend_to_changelog(changelog_path, new_block, full_version)
        elif not string_in_file_if_exists(changelog_path, full_version):
            error2(f"Missing changelog version: {full_version}")
    
    if args.version or args.properties:
        info2(f"Updating gradle.properties...")
        gradle_properties_path = f"{project_path}/gradle.properties"
        gradle_properties = create_gradle_properties(args)
        update_gradle_properties(gradle_properties_path, gradle_properties)

    if args.gradle:
        info2(f"Updating gradle-wrapper.properties...")
        gradle_wrapper_properties_path = f"{project_path}/gradle/wrapper/gradle-wrapper.properties"
        update_gradle_properties(gradle_wrapper_properties_path, {
            "distributionUrl": f"https\\://services.gradle.org/distributions/gradle-{args.gradle}-bin.zip"
        })
        subprocess.run(["./gradlew", "wrapper", "--gradle-version", args.gradle], cwd=project_path, check=True)

    if args.upgrade:
        info2("Applying Spotless...")
        if args.upgrade == "1.21.11":
            subprocess.run(["./gradlew", "all-mountsofmayhem-apply"], cwd=project_path, check=True)
        elif args.upgrade == "1.21.10":
            subprocess.run(["./gradlew", "all-thecopperage-apply"], cwd=project_path, check=True)

        subprocess.run(["./gradlew", "all-java-apply"], cwd=project_path, check=True)

    info2("Refreshing project...")
    if args.legacy:
        subprocess.run(["./gradlew"], cwd=project_path, check=True)
    else:
        subprocess.run(["./gradlew", "all-validate"], cwd=project_path, check=True)

    if args.sources:
        info2("Generating sources...")
        subprocess.run(["./gradlew", "commonGenSources" if args.legacy else "common-sources"], cwd=project_path, check=True)

    if args.data:
        info2("Running data generation...")
        subprocess.run(["./gradlew", "neoForgeData" if args.legacy else "neoforge-data"], cwd=project_path, check=True)

    for parameter_set in launch_parameters:
        info2(f"Launching {parameter_set[0].capitalize()} {parameter_set[1].capitalize()}...")
        run_launch(parameter_set[0], parameter_set[1], project_path, args.legacy)

    if args.version and args.commit:
        info2(f"Commiting version v{args.version}...")
        git_push_all(args, project_path, f"release v{args.version}")

    if args.version and args.publish:
        info2(f"Publishing version v{args.version}...")
        subprocess.run(["./gradlew", "allPublish" if args.legacy else "all-publish"], cwd=project_path, check=True)

    if args.version and upload_parameters:
        info2(f"Uploading version v{args.version}{f" for {upload_parameters[0].capitalize()}" if upload_parameters[0] else ""}{f" to {upload_parameters[1].capitalize()}" if upload_parameters[1] else ""}...")
        run_upload(upload_parameters[0], upload_parameters[1], project_path, args.legacy)

    if args.version and args.notify:
        info2(f"Notifying version v{args.version}...")
        subprocess.run(["./gradlew", "notifyDiscord" if args.legacy else "all-discord"], cwd=project_path, check=True)

if __name__ == "__main__":
    main()
    