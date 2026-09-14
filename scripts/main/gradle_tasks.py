#!/usr/bin/env python3
"""Gradle task dispatch for launching and uploading.

Purpose: map validated ``(loader, distribution)`` and ``(loader, site)`` pairs
to the Gradle task names that launch a game client/server or publish to the
distribution sites, keeping the legacy task names in one place.

Entry points: ``main.py`` calls ``run_launch`` and ``run_upload``.

Side effects: runs ``./gradlew`` in the project directory and exits via
``error2`` for unsupported launch values.

Constraints: standard library only; must be invoked from a project containing
the Gradle wrapper. ``legacy_tasks=True`` selects the old camelCase task
names.
"""

import subprocess

from console import error2


def run_launch(mod_loader, distribution, project_path, legacy_tasks=False):
    """Run the Gradle launch task for a loader and distribution.

    Args:
        mod_loader: ``"fabric"`` or ``"neoforge"``.
        distribution: ``"client"`` or ``"server"``.
        project_path: Project directory containing ``gradlew``.
        legacy_tasks: Use legacy camelCase task names.

    Side effects: runs ``./gradlew``; exits via ``error2`` for unsupported
    arguments.
    """
    if mod_loader == "fabric":
        if distribution == "client":
            subprocess.run(["./gradlew", "fabricClient" if legacy_tasks else "fabric-client"], cwd=project_path, check=True)
        elif distribution == "server":
            subprocess.run(["./gradlew", "fabricServer" if legacy_tasks else "fabric-server"], cwd=project_path, check=True)
        else:
            error2(f"Unsupported argument: {distribution}")
    elif mod_loader == "neoforge":
        if distribution == "client":
            subprocess.run(["./gradlew", "neoForgeClient" if legacy_tasks else "neoforge-client"], cwd=project_path, check=True)
        elif distribution == "server":
            subprocess.run(["./gradlew", "neoForgeServer" if legacy_tasks else "neoforge-server"], cwd=project_path, check=True)
        else:
            error2(f"Unsupported argument: {distribution}")
    else:
        error2(f"Unsupported argument: {mod_loader}")


def run_upload(mod_loader, website, project_path, legacy_tasks=False):
    """Run the Gradle upload task for a loader and site.

    A ``mod_loader`` of None selects the aggregate ``all-*`` task; a
    ``website`` of None selects the loader's "everywhere" task. Unrecognized
    values fall through to those same aggregate tasks.

    Args:
        mod_loader: ``"fabric"``, ``"neoforge"``, or None for all loaders.
        website: ``"curseforge"``, ``"modrinth"``, ``"github"``, or None for
            all sites.
        project_path: Project directory containing ``gradlew``.
        legacy_tasks: Use legacy camelCase task names.

    Side effects: runs ``./gradlew``.
    """
    if mod_loader == "fabric":
        if website == "curseforge":
            subprocess.run(["./gradlew", "fabricUploadCurseForge" if legacy_tasks else "fabric-curseforge"], cwd=project_path, check=True)
        elif website == "modrinth":
            subprocess.run(["./gradlew", "fabricUploadModrinth" if legacy_tasks else "fabric-modrinth"], cwd=project_path, check=True)
        elif website == "github":
            subprocess.run(["./gradlew", "fabricUploadGitHub" if legacy_tasks else "fabric-github"], cwd=project_path, check=True)
        else:
            subprocess.run(["./gradlew", "fabricUploadEverywhere" if legacy_tasks else "fabric-all"], cwd=project_path, check=True)
    elif mod_loader == "neoforge":
        if website == "curseforge":
            subprocess.run(["./gradlew", "neoForgeUploadCurseForge" if legacy_tasks else "neoforge-curseforge"], cwd=project_path, check=True)
        elif website == "modrinth":
            subprocess.run(["./gradlew", "neoForgeUploadModrinth" if legacy_tasks else "neoforge-modrinth"], cwd=project_path, check=True)
        elif website == "github":
            subprocess.run(["./gradlew", "neoForgeUploadGitHub" if legacy_tasks else "neoforge-github"], cwd=project_path, check=True)
        else:
            subprocess.run(["./gradlew", "neoForgeUploadEverywhere" if legacy_tasks else "neoforge-all"], cwd=project_path, check=True)
    else:
        if website == "curseforge":
            subprocess.run(["./gradlew", "allUploadCurseForge" if legacy_tasks else "all-curseforge"], cwd=project_path, check=True)
        elif website == "modrinth":
            subprocess.run(["./gradlew", "allUploadModrinth" if legacy_tasks else "all-modrinth"], cwd=project_path, check=True)
        elif website == "github":
            subprocess.run(["./gradlew", "allUploadGitHub" if legacy_tasks else "all-github"], cwd=project_path, check=True)
        else:
            subprocess.run(["./gradlew", "allUploadEverywhere" if legacy_tasks else "all-all"], cwd=project_path, check=True)
