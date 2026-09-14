#!/usr/bin/env python3
"""Dispatch to the Gradle tasks for launching and uploading a project."""

import subprocess

from console import error2


def run_launch(mod_loader, distribution, project_path, legacy_tasks=False):
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
