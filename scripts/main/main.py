#!/usr/bin/env python3
"""Core CLI entry point for modresources project management tasks.

Orchestrates version cloning, workspace upgrades, Gradle property updates,
changelog handling, building, launching, publishing, and uploading. Heavier
logic lives in the sibling modules; this file owns argument parsing dispatch
and task ordering.
"""

import os
import subprocess
import sys

import clone_versions
from changelog import generate_changelog_block, parse_changelog_sections, prepend_to_changelog
from cli import parse_args
from console import error2, info2, warn2
from fs_utils import has_subproject, string_in_file_if_exists
from git_ops import git_push_all, prepare_new_version
from gradle_properties import create_gradle_properties, find_gradle_property, update_gradle_properties
from gradle_tasks import run_launch, run_upload
from validation import (
    validate_launch_parameters,
    validate_legacy_parameter,
    validate_open_parameters,
    validate_upload_parameters,
)
from workspace_upgrade import run_workspace_upgrade


def update_directory(args, path):
    if os.path.isdir(path):
        if not args.open and not args.bare:
            subprocess.run(["git", "pull"], cwd=path, check=True)
    else:
        error2(f"Directory not found: {path}")


def main():
    args = parse_args()
    base_path = find_gradle_property("fuzs.multiloader.project.mods")
    root_path = args.path or os.path.join(base_path, args.name)
    main_path = os.path.join(root_path, "main")
    project_path = os.path.join(root_path, args.minecraft)

    if args.init:
        info2(f"Running init at {root_path}...")
        if isinstance(args.init, str) and not args.version:
            error2(f"--init {args.init} requires --version to prepare a new version branch")
        if args.version and isinstance(args.init, str):
            clone_versions.setup_git(root_path, args.name)
            info2(f"Preparing Minecraft version {args.minecraft}...")
            prepare_new_version(args, root_path, project_path)
        else:
            clone_versions.setup_git(root_path, args.name, [args.minecraft])

    update_directory(args, main_path)
    update_directory(args, project_path)

    environment = validate_open_parameters(args.open, "finder")
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
                warn2(f"Could not launch IntelliJ: {e}")
        sys.exit(0)

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

    legacy = validate_legacy_parameter(args.legacy)
    legacy_properties = "properties" in legacy
    legacy_tasks = "tasks" in legacy

    updated_gradle_properties = create_gradle_properties(args, legacy_properties)
    if updated_gradle_properties:
        info2(f"Updating gradle.properties...")

    gradle_properties_path = f"{project_path}/gradle.properties"
    gradle_properties_remove_predicate = lambda key: key.startswith("project.libs.") if args.upgrade else None
    gradle_properties = update_gradle_properties(
        gradle_properties_path,
        updated_gradle_properties,
        remove_predicate=gradle_properties_remove_predicate
    )
    if args.version:
        version_key = "modVersion" if legacy_properties else "mod.version"
        if version_key not in gradle_properties:
            error2(f"Missing property {version_key} in {gradle_properties_path}")
        args.version = gradle_properties[version_key]

    if args.changelog and not args.version:
        warn2("Skipping changelog: --version is required")

    if args.version:
        changelog_path = f"{project_path}/CHANGELOG.md"
        full_version = f"v{args.version}-mc{args.minecraft}"
        changelog_section_data = parse_changelog_sections(args.changelog)

        if changelog_section_data:
            info2(f"Updating CHANGELOG.md...")
            new_block = generate_changelog_block(full_version, changelog_section_data)
            prepend_to_changelog(changelog_path, new_block, full_version)
        elif not string_in_file_if_exists(changelog_path, full_version):
            error2(f"Missing changelog version: {full_version}")

    if args.gradle:
        info2(f"Updating gradle-wrapper.properties...")
        gradle_wrapper_properties_path = f"{project_path}/gradle/wrapper/gradle-wrapper.properties"
        update_gradle_properties(gradle_wrapper_properties_path, {
            "distributionUrl": f"https\\://services.gradle.org/distributions/gradle-{args.gradle}-bin.zip"
        })

        if not args.bare:
            subprocess.run(["./gradlew", "wrapper", "--gradle-version", args.gradle], cwd=project_path, check=True)

    if args.spotless and not args.bare:
        if args.spotless == "tinytakeover":
            info2("Applying Spotless for Tiny Takeover...")
            subprocess.run(["./gradlew", "all-tinytakeover-apply"], cwd=project_path, check=True)
        elif args.spotless == "mountsofmayhem":
            info2("Applying Spotless for Mounts Of Mayhem...")
            subprocess.run(["./gradlew", "all-mountsofmayhem-apply"], cwd=project_path, check=True)
        elif args.spotless == "thecopperage":
            info2("Applying Spotless for The Copper Age...")
            subprocess.run(["./gradlew", "all-thecopperage-apply"], cwd=project_path, check=True)

        subprocess.run(["./gradlew", "all-java-apply"], cwd=project_path, check=True)

    if not args.bare:
        info2("Refreshing project...")
        subprocess.run(["./gradlew"], cwd=project_path, check=True)
        if has_subproject(project_path, "Fabric"):
            subprocess.run(["./gradlew", ":Fabric:fabric-validate"], cwd=project_path, check=True)

    if args.data and not args.bare:
        info2("Running data generation...")
        subprocess.run(["./gradlew", "neoForgeData" if legacy_tasks else "neoforge-data"], cwd=project_path, check=True)

    if not args.bare:
        launch_parameters = [
            validate_launch_parameters(project_path, launch)
            for launch in args.launch
        ]
        for parameter_set in launch_parameters:
            info2(f"Launching {parameter_set[0].capitalize()} {parameter_set[1].capitalize()}...")
            run_launch(parameter_set[0], parameter_set[1], project_path, legacy_tasks)

    if args.commit:
        if args.version:
            info2(f"Commiting version v{args.version}...")
            git_push_all(args, project_path, f"release v{args.version}")
        else:
            warn2("Skipping commit: --version is required")

    if args.publish and not args.bare:
        if args.version:
            info2(f"Publishing version v{args.version}...")
            subprocess.run(["./gradlew", "allPublish" if legacy_tasks else "all-publish"], cwd=project_path, check=True)
        else:
            warn2("Skipping publish: --version is required")

    if not args.bare:
        upload_parameters = validate_upload_parameters(args.upload)
        if upload_parameters:
            if args.version:
                upload_loader = f" for {upload_parameters[0].capitalize()}" if upload_parameters[0] else ""
                upload_site = f" to {upload_parameters[1].capitalize()}" if upload_parameters[1] else ""
                info2(f"Uploading version v{args.version}{upload_loader}{upload_site}...")
                run_upload(upload_parameters[0], upload_parameters[1], project_path, legacy_tasks)
            else:
                warn2("Skipping upload: --version is required")

    if args.notify and not args.bare:
        if args.version:
            info2(f"Announcing version v{args.version}...")
            subprocess.run(["./gradlew", "notifyDiscord" if legacy_tasks else "all-discord"], cwd=project_path, check=True)
        else:
            warn2("Skipping announce: --version is required")


if __name__ == "__main__":
    main()
