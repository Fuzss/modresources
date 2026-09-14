#!/usr/bin/env python3
"""Workspace upgrade routines for Minecraft version transitions.

Purpose: refresh a project's ``main`` workspace from the multiloader template
and apply the version-specific migrations needed to move a project branch to a
newer Minecraft version.

Entry points: ``main.py`` calls ``run_workspace_upgrade`` when ``--upgrade``
is set.

Side effects: runs git and subprocess commands, copies template files, deletes
obsolete files, rewrites Gradle files, and optionally commits. Aborts via
``error2`` when a worktree is dirty.

Constraints: standard library only. The ``main`` and project worktrees must be
clean before an upgrade starts. Step order matters: templates are copied
first, then mixin and property migrations run, then legacy files are removed.
"""

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
    """Apply the 26.1.x resource and build-script renames.

    Renames ``mod_logo.png`` to ``pack.png`` and the ``.accesswidener`` file
    to ``.classtweaker``, rewrites its header to ``classTweaker v2``, and
    switches ``libs.`` catalog references to ``sharedLibs.`` in the three
    build scripts.

    Args:
        mod_id: Mod ID used in the access-widener file name.
        project_path: Project branch to rewrite.

    Side effects: moves and rewrites files under ``project_path``.
    """
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
    """Apply the 1.21.11 migration.

    Copies the root Gradle settings and build script and the per-module
    ``gradle.properties`` from ``template_path`` (per-module
    ``build.gradle.kts`` only when absent), converts each module's mixin JSON
    to Gradle DSL, migrates the project properties, then deletes the
    superseded legacy Gradle and metadata files.

    Args:
        mod_id: Mod ID used to locate mixin and metadata files.
        template_path: Multiloader template for the target version.
        project_path: Project branch to migrate.
        plugins_version: Convention plugins version for the properties
            migration.

    Side effects: copies, rewrites, and deletes files under ``project_path``.
    """
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
    """Apply the 1.21.1 migration by composing the 1.21.11 and 26.1 steps."""
    run_1_21_11_upgrade(mod_id, template_path, project_path, plugins_version)
    run_26_1_upgrade(mod_id, project_path)


def run_workspace_upgrade(args, base_path, main_path, project_path):
    """Refresh ``main`` and migrate the target version branch.

    Validates that both worktrees are clean and pulls them. Refreshes ``main``
    from the template (``.gitignore``, ``.github``, license year) and commits
    when ``--commit`` is set. On the project branch it removes the stale
    ``CHANGELOG.md``, ``pack.mcmeta``, and ``mod_banner.png``, runs the
    version-specific upgrade named by ``--upgrade``, and commits when
    ``--commit`` is set.

    Args:
        args: Parsed CLI arguments (``minecraft``, ``upgrade``, ``plugins``,
            ``id``, ``commit``).
        base_path: Root containing the mod repositories.
        main_path: The project's ``main`` worktree.
        project_path: The target Minecraft version worktree.

    Side effects: git subprocesses, template copies, file deletions, and
    commits. Aborts via ``error2`` when a worktree is dirty.
    """
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
