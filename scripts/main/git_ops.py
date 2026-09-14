#!/usr/bin/env python3
"""Git operations for pushing changes and preparing new version branches."""

import os
import subprocess

from console import error2, warn2
from fs_utils import copy_from_template


def git_push_all(args, repo_path, commit_message):
    remote_url = f"git@github.com:Fuzss/{args.name}.git"

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


def parse_minecraft_version(branch: str) -> tuple[int, ...] | None:
    try:
        parts = branch.strip().lower().split(".")
        numbers = tuple(int(part) for part in parts if part not in ("", "x"))
        return numbers if numbers else None
    except (ValueError, AttributeError):
        return None


def is_version_upgrade(source_branch: str, new_branch: str) -> bool:
    source_version = parse_minecraft_version(source_branch)
    target_version = parse_minecraft_version(new_branch)
    if source_version is None or target_version is None:
        return False
    return target_version > source_version


def prepare_new_version(args, root_path, project_path):
    remote_url = f"git@github.com:Fuzss/{args.name}.git"
    new_branch = args.minecraft
    source_branch = args.init

    if os.path.isdir(project_path):
        warn2(f"Branch {new_branch} already exists, skipping")
        return

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

    if is_version_upgrade(source_branch, new_branch):
        source_path = os.path.join(root_path, args.init)
        copy_from_template(os.path.join(source_path, "run"), os.path.join(project_path, "run"), only_if_absent=True, throw_when_not_found=False)
    else:
        print(f"Skipping run directory copy: {source_branch} -> {new_branch} is not an upgrade")
