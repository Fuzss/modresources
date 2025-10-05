#!/usr/bin/env python3
import shutil
import sys
import os
import subprocess
import argparse
import re
import json
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

    parser.add_argument('--path', type=str, default=None, metavar="ROOT_PATH", help="Override default root path. Example: --path /absolute/path/to/project.")
    parser.add_argument('--copy', type=str, default=None, metavar="LEGACY_GAME_VERSION", help="Copy from existing game version. Example: --copy 1.21.5.")
    parser.add_argument('--move', type=str, default=None, metavar="LEGACY_GAME_VERSION", help="Move existing game version. Example: --move 1.21.7.")
    parser.add_argument('--upgrade', default=False, action="store_true", help="Run workspace upgrade.")
    parser.add_argument('--gradle', type=str, default=None, metavar="GRADLE_VERSION", help="Gradle wrapper version. Example: --gradle 8.14.3.")
    parser.add_argument('--id', type=str, required=True, metavar="MOD_ID", help="Mod id. Example: --id examplemod.")
    parser.add_argument('--version', type=str, default=None, metavar="PROJECT_VERSION", help="Mod version. Example: --version 21.8.0.")
    parser.add_argument('--minecraft', type=str, required=True, metavar="GAME_VERSION", help="Game version. Example: --minecraft 1.21.8.")
    parser.add_argument('--catalog', type=str, default=None, metavar="VERSION_CATALOG", help="Version catalog version. Example: --catalog v1.")
    parser.add_argument('--data', default=False, action="store_true", help="Generate data.")
    parser.add_argument('--launch', default=[], action="append", nargs="*", metavar=("MOD_LOADER", "DISTRIBUTION"), help="Launch the game. Format: --launch MOD_LOADER DISTRIBUTION. Can be used multiple times.")
    parser.add_argument('--commit', default=False, action="store_true", help="Commit to GitHub.")
    parser.add_argument('--upload', default=None, nargs="*", metavar=("MOD_LOADER", "WEBSITE"), help="Upload to CurseForge, Modrinth, or GitHub. Format: --upload MOD_LOADER WEBSITE.")
    parser.add_argument('--open', default=None, nargs="*", metavar="ENVIRONMENT", help="Open in Finder, or Idea. Format: --open ENVIRONMENT.")
    parser.add_argument('--publish', default=False, action="store_true", help="Publish to Maven.")
    parser.add_argument('--notify', default=False, action="store_true", help="Notify via Discord webhook.")
    parser.add_argument("--changelog", default=None, action="append", nargs=2, metavar=("SECTION", "LINE"), help="Add a changelog line. Format: --changelog SECTION LINE. Can be used multiple times.")

    args = parser.parse_args()
    
    if args.move or args.copy:
        if not args.data:
            args.data = True
        if not args.upgrade:
            args.upgrade = True
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

def copy_from_template(source_path, destination_path):
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

def remove_directory_or_file(file_path):
    if os.path.isdir(file_path):
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
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or '=' not in line:
            new_lines.append(line)
            continue

        key, _ = line.split('=', 1)
        key = key.strip()
        if key in updates:
            new_value = updates[key]
            if new_value == "#":
                new_lines.append(f"#{line}")
            elif new_value is not None:
                new_lines.append(f"{key}={new_value}\n")
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

def git_push_all(repo_path, project_name, commit_message):
    token = find_gradle_property("githubCommitToken")
    remote_url = f"https://{token}@github.com/Fuzss/{project_name}.git"
    commands = [
        ["git", "remote", "set-url", "origin", remote_url],
        ["git", "add", "."],
        ["git", "commit", "-m", commit_message],
        ["git", "push"]
    ]
    for cmd in commands:
        subprocess.run(cmd, cwd=repo_path, check=True)

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

def create_gradle_properties(mod_version, minecraft_version, version_catalog):
    gradle_properties = {
        "modVersion": mod_version,
        "dependenciesPuzzlesLibVersion": "#",
        "dependenciesMinPuzzlesLibVersion": "#",
        "dependenciesRequiredForgeCurseForge": None,
        "dependenciesRequiredForgeModrinth": None,
        "dependenciesOptionalFabricCurseForge": None,
        "dependenciesOptionalNeoForgeCurseForge": None,
        "dependenciesOptionalForgeCurseForge": None,
        "dependenciesOptionalFabricModrinth": None,
        "dependenciesOptionalNeoForgeModrinth": None,
        "dependenciesOptionalForgeModrinth": None
    }

    if version_catalog is not None:
        gradle_properties["dependenciesVersionCatalog"] = f"{minecraft_version}-{version_catalog}"

    return gradle_properties

def run_launch(mod_loader, distribution, project_path):
    if mod_loader == "fabric":
        if distribution == "client":
            subprocess.run(["./gradlew", "fabricClient"], cwd=project_path, check=True)
        elif distribution == "server":
            subprocess.run(["./gradlew", "fabricServer"], cwd=project_path, check=True)
        else:
            error2(f"Unsupported argument: {distribution}")
    elif mod_loader == "neoforge":
        if distribution == "client":
            subprocess.run(["./gradlew", "neoForgeClient"], cwd=project_path, check=True)
        elif distribution == "server":
            subprocess.run(["./gradlew", "neoForgeServer"], cwd=project_path, check=True)
        else:
            error2(f"Unsupported argument: {distribution}")
    else:
        error2(f"Unsupported argument: {mod_loader}")

def run_upload(mod_loader, website, project_path):
    if mod_loader == "fabric":
        if website == "curseforge":
            subprocess.run(["./gradlew", "fabricUploadCurseForge"], cwd=project_path, check=True)
        elif website == "modrinth":
            subprocess.run(["./gradlew", "fabricUploadModrinth"], cwd=project_path, check=True)
        elif website == "github":
            subprocess.run(["./gradlew", "fabricUploadGitHub"], cwd=project_path, check=True)
        else:
            subprocess.run(["./gradlew", "fabricUploadEverywhere"], cwd=project_path, check=True)
    elif mod_loader == "neoforge":
        if website == "curseforge":
            subprocess.run(["./gradlew", "neoForgeUploadCurseForge"], cwd=project_path, check=True)
        elif website == "modrinth":
            subprocess.run(["./gradlew", "neoForgeUploadModrinth"], cwd=project_path, check=True)
        elif website == "github":
            subprocess.run(["./gradlew", "neoForgeUploadGitHub"], cwd=project_path, check=True)
        else:
            subprocess.run(["./gradlew", "neoForgeUploadEverywhere"], cwd=project_path, check=True)
    else:
        if website == "curseforge":
            subprocess.run(["./gradlew", "allUploadCurseForge"], cwd=project_path, check=True)
        elif website == "modrinth":
            subprocess.run(["./gradlew", "allUploadModrinth"], cwd=project_path, check=True)
        elif website == "github":
            subprocess.run(["./gradlew", "allUploadGitHub"], cwd=project_path, check=True)
        else:
            subprocess.run(["./gradlew", "allUploadEverywhere"], cwd=project_path, check=True)

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
    if args.move:
        projectSource = f"{root_path}/{args.move}"
        if os.path.isdir(projectSource):
            shutil.move(projectSource, project_path)
            print(f"Moved {projectSource} -> {project_path}")
        else:
            error2(f"Failed to move: {projectSource} -> {project_path}")

    if args.copy:
        projectSource = f"{root_path}/{args.copy}"
        if os.path.isdir(projectSource):
            shutil.copytree(projectSource, project_path)
            print(f"Copied {projectSource} -> {project_path}")
        else:
            error2(f"Failed to copy: {projectSource} -> {project_path}")

    remove_directory_or_file(f"{project_path}/.idea")
    remove_directory_or_file(f"{project_path}/.gradle")
    remove_directory_or_file(f"{project_path}/CHANGELOG.md")

    if args.commit:
        git_push_all(f"{root_path}", args.id, f"prepare {args.minecraft} port")
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

def run_workspace_upgrade(args, base_path, root_path, project_path):
    template_path = f"{base_path}/multiloader-workspace-template"
    copy_from_template(f"{template_path}/.gitignore", f"{root_path}/.gitignore")
    copy_from_template(f"{template_path}/.github", f"{root_path}/.github")

    update_license_year(f"{root_path}/LICENSE-ASSETS.md")

    remove_directory_or_file(f"{project_path}/Common/src/main/resources/pack.mcmeta")
    remove_directory_or_file(f"{project_path}/Common/src/main/resources/mod_banner.png")

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

    if args.commit:
        git_push_all(f"{root_path}", args.id, f"upgrade {args.minecraft} workspace")
        print("Committed workspace upgrades")

def main():
    args = parse_args()
    base_path = find_gradle_property("modRoot")
    root_path = args.path or f"{base_path}/{args.id}"
    project_path = f"{root_path}/{args.minecraft}"
    environment = validate_open_parameters(args.open, "finder")
    changelog_section_data = parse_changelog_sections(args.changelog)
    launch_parameters = [ 
        validate_launch_parameters(launch, ("fabric", "client")) 
        for launch in args.launch 
    ]
    upload_parameters = validate_upload_parameters(args.upload)

    if args.version and args.catalog and (args.move or args.copy):
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
                subprocess.Popen(["/Applications/IntelliJ IDEA.app/Contents/MacOS/idea", project_path], cwd=project_path)
            except FileNotFoundError as e:
                warn2("Could not launch IntelliJ:", e)
        sys.exit(1)

    if args.upgrade:
        info2("Upgrading workspace...")
        run_workspace_upgrade(args, base_path, root_path, project_path)

    if args.version:
        changelog_path = f"{project_path}/CHANGELOG.md"
        full_version = f"v{args.version}-{args.minecraft}"

        if changelog_section_data:
            info2(f"Updating CHANGELOG.md...")
            new_block = generate_changelog_block(full_version, changelog_section_data)
            prepend_to_changelog(changelog_path, new_block, full_version)
        elif not string_in_file_if_exists(changelog_path, full_version):
            error2(f"Missing changelog version: {full_version}")
    
    if args.version:
        info2(f"Updating gradle.properties...")
        gradle_properties_path = f"{project_path}/gradle.properties"
        gradle_properties = create_gradle_properties(args.version, args.minecraft, args.catalog)
        update_gradle_properties(gradle_properties_path, gradle_properties)

    if args.gradle:
        info2(f"Updating gradle-wrapper.properties...")
        gradle_wrapper_properties_path = f"{project_path}/gradle/wrapper/gradle-wrapper.properties"
        update_gradle_properties(gradle_wrapper_properties_path, {
            "distributionUrl": f"https\\://services.gradle.org/distributions/gradle-{args.gradle}-bin.zip"
        })
        info2("Refreshing project...")
        subprocess.run(["./gradlew", "wrapper", "--gradle-version", args.gradle], cwd=project_path, check=True)

    if args.version and args.catalog:
        info2("Generating sources...")
        subprocess.run(["./gradlew", "commonGenSources"], cwd=project_path, check=True)
    elif not args.gradle:
        info2("Refreshing project...")
        subprocess.run(["./gradlew"], cwd=project_path, check=True)

    if args.data:
        info2("Running data generation...")
        subprocess.run(["./gradlew", "neoForgeData"], cwd=project_path, check=True)

    for parameter_set in launch_parameters:
        info2(f"Launching {parameter_set[0].capitalize()} {parameter_set[1].capitalize()}...")
        run_launch(parameter_set[0], parameter_set[1], project_path)

    if args.version and args.commit:
        info2(f"Commiting version v{args.version}...")
        git_push_all(f"{root_path}", args.id, f"release v{args.version}")

    if args.version and args.publish:
        info2(f"Publishing version v{args.version}...")
        subprocess.run(["./gradlew", "allPublish"], cwd=project_path, check=True)

    if args.version and upload_parameters:
        info2(f"Uploading version v{args.version}{f" for {upload_parameters[0].capitalize()}" if upload_parameters[0] else ""}{f" to {upload_parameters[1].capitalize()}" if upload_parameters[1] else ""}...")
        run_upload(upload_parameters[0], upload_parameters[1], project_path)

    if args.version and args.notify:
        info2(f"Notifying version v{args.version}...")
        subprocess.run(["./gradlew", "notifyDiscord"], cwd=project_path, check=True)

if __name__ == "__main__":
    main()
    