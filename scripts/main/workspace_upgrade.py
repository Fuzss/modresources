#!/usr/bin/env python3
"""Workspace upgrade routines for individual Minecraft version transitions."""

import os
import subprocess

import migrate_mixins
import migrate_mod_properties
from console import error2
from fs_utils import (
    copy_from_template,
    move_directory_or_file,
    remove_directory_or_file,
    replace_text_block,
    update_license_year,
)
from git_ops import git_push_all


# Upgrade targets that only need the generic workspace refresh and have no
# version-specific migration steps of their own.
GENERIC_UPGRADES = {"26.2.x"}


def run_26_1_upgrade(mod_id, project_path):
    move_directory_or_file(
        os.path.join(project_path, "Common", "src", "main", "resources", "mod_logo.png"),
        os.path.join(project_path, "Common", "src", "main", "resources", "pack.png")
    )

    move_directory_or_file(
        os.path.join(project_path, "Common", "src", "main", "resources", f"{mod_id}.accesswidener"),
        os.path.join(project_path, "Common", "src", "main", "resources", f"{mod_id}.classtweaker")
    )

    replace_text_block(
        os.path.join(project_path, "Common", "src", "main", "resources", f"{mod_id}.classtweaker"),
        r"^accessWidener\s+v[12]\s+\w+\s*$",
        "classTweaker    v2  official"
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


def run_1_21_11_upgrade(mod_id, template_path, project_path, plugins_version):
    copy_from_template(f"{template_path}/settings.gradle.kts", f"{project_path}/settings.gradle.kts")
    copy_from_template(f"{template_path}/build.gradle.kts", f"{project_path}/build.gradle.kts")
    copy_from_template(f"{template_path}/Common/build.gradle.kts", f"{project_path}/Common/build.gradle.kts", only_if_absent=True)
    copy_from_template(f"{template_path}/Common/gradle.properties", f"{project_path}/Common/gradle.properties")
    copy_from_template(f"{template_path}/Fabric/build.gradle.kts", f"{project_path}/Fabric/build.gradle.kts", only_if_absent=True)
    copy_from_template(f"{template_path}/Fabric/gradle.properties", f"{project_path}/Fabric/gradle.properties")
    copy_from_template(f"{template_path}/NeoForge/build.gradle.kts", f"{project_path}/NeoForge/build.gradle.kts", only_if_absent=True)
    copy_from_template(f"{template_path}/NeoForge/gradle.properties", f"{project_path}/NeoForge/gradle.properties")

    migrate_mixins.convert_mixins(f"{project_path}/Common/src/main/resources/common.mixins.json", f"{project_path}/Common/build.gradle.kts")
    migrate_mixins.convert_mixins(f"{project_path}/Common/src/main/resources/{mod_id}.common.mixins.json", f"{project_path}/Common/build.gradle.kts")
    migrate_mixins.convert_mixins(f"{project_path}/Fabric/src/main/resources/fabric.mixins.json", f"{project_path}/Fabric/build.gradle.kts")
    migrate_mixins.convert_mixins(f"{project_path}/Fabric/src/main/resources/{mod_id}.fabric.mixins.json", f"{project_path}/Fabric/build.gradle.kts")
    migrate_mixins.convert_mixins(f"{project_path}/NeoForge/src/main/resources/neoforge.mixins.json", f"{project_path}/NeoForge/build.gradle.kts")
    migrate_mixins.convert_mixins(f"{project_path}/NeoForge/src/main/resources/{mod_id}.neoforge.mixins.json", f"{project_path}/NeoForge/build.gradle.kts")
    migrate_mod_properties.migrate_properties(f"{project_path}/gradle.properties", f"{project_path}/gradle.properties", plugins_version)

    remove_directory_or_file(f"{project_path}/settings.gradle")
    remove_directory_or_file(f"{project_path}/build.gradle")
    remove_directory_or_file(f"{project_path}/Common/build.gradle")
    remove_directory_or_file(f"{project_path}/Common/src/main/resources/architectury.common.json")
    remove_directory_or_file(f"{project_path}/Common/src/main/resources/common.mixins.json")
    remove_directory_or_file(f"{project_path}/Common/src/main/resources/{mod_id}.common.mixins.json")
    remove_directory_or_file(f"{project_path}/Fabric/build.gradle")
    remove_directory_or_file(f"{project_path}/Fabric/src/main/resources/fabric.mod.json")
    remove_directory_or_file(f"{project_path}/Fabric/src/main/resources/fabric.mixins.json")
    remove_directory_or_file(f"{project_path}/Fabric/src/main/resources/{mod_id}.fabric.mixins.json")
    remove_directory_or_file(f"{project_path}/NeoForge/build.gradle")
    remove_directory_or_file(f"{project_path}/NeoForge/src/main/resources/META-INF/neoforge.mods.toml")
    remove_directory_or_file(f"{project_path}/NeoForge/src/main/resources/META-INF", only_if_empty=True)
    remove_directory_or_file(f"{project_path}/NeoForge/src/main/resources/neoforge.mixins.json")
    remove_directory_or_file(f"{project_path}/NeoForge/src/main/resources/{mod_id}.neoforge.mixins.json")


def run_1_21_1_upgrade(mod_id, template_path, project_path, plugins_version):
    run_1_21_11_upgrade(mod_id, template_path, project_path, plugins_version)
    run_26_1_upgrade(mod_id, project_path)


def run_workspace_upgrade(args, base_path, main_path, project_path):
    template_root_path = os.path.join(base_path, "multiloader-workspace-template")
    template_main_path = os.path.join(template_root_path, "main")
    template_project_path = os.path.join(template_root_path, args.minecraft)

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=main_path,
        capture_output=True,
        text=True,
        check=True
    )
    if result.stdout.strip() != "":
        error2("Worktree main not clean, unable to run upgrade")

    subprocess.run(["git", "pull"], cwd=main_path, check=True)

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

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=project_path,
        capture_output=True,
        text=True,
        check=True
    )
    if result.stdout.strip() != "":
        error2(f"Worktree {args.minecraft} not clean, unable to run upgrade")

    subprocess.run(["git", "pull"], cwd=project_path, check=True)

    remove_directory_or_file(f"{project_path}/CHANGELOG.md")

    remove_directory_or_file(
        os.path.join(project_path, "Common", "src", "main", "resources", "pack.mcmeta")
    )

    remove_directory_or_file(
        os.path.join(project_path, "Common", "src", "main", "resources", "mod_banner.png")
    )

    if isinstance(args.upgrade, str):
        print(f"Running {args.upgrade} workspace upgrades")
        if args.upgrade == "26.1.x":
            run_26_1_upgrade(args.id, project_path)
        elif args.upgrade == "1.21.11":
            run_1_21_11_upgrade(args.id, template_project_path, project_path, args.plugins)
        elif args.upgrade == "1.21.1":
            run_1_21_1_upgrade(args.id, template_project_path, project_path, args.plugins)
        elif args.upgrade not in GENERIC_UPGRADES:
            error2(f"Unsupported upgrade target: {args.upgrade}")

    if args.commit and git_push_all(args, project_path, f"upgrade {args.minecraft} workspace"):
        print(f"Committed workspace upgrades on {args.minecraft}")
