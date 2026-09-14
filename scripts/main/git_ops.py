#!/usr/bin/env python3
"""Git operations for version branches and commits.

Purpose: own the git side of the CLI: staging, committing, and pushing a
repository, and cloning a new Minecraft version branch from an existing one.

Entry points: ``main.py`` calls ``git_push_all`` and ``prepare_new_version``;
``clone_versions`` and ``workspace_upgrade`` also use them.

Side effects: runs ``git`` subprocesses (set-url, add, diff, commit, push,
ls-remote, clone, checkout) in the target repository and may copy a template
``run`` directory. Prints progress lines.

Constraints: standard library only; requires a git installation and SSH
credentials for ``git@github.com:Fuzss/<name>.git``.
"""

import os
import subprocess

from console import error2, warn2
from fs_utils import copy_from_template


def git_push_all(args, repo_path, commit_message):
    """Stage everything in ``repo_path`` and commit/push when there is a change.

    The ``origin`` remote is first repointed to
    ``git@github.com:Fuzss/<args.name>.git``.

    Args:
        args: Parsed CLI arguments; ``args.name`` supplies the remote URL.
        repo_path: Repository working tree to commit in.
        commit_message: Message for the created commit.

    Returns:
        True when a commit and push happened, False when there was nothing
        staged.

    Side effects: runs git subprocesses; prints a line when it skips.
    """
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
    """Parse a branch name into a numeric version tuple, or None.

    Empty components and ``x`` placeholders are dropped, so ``"26.2.x"``
    becomes ``(26, 2)``. Returns None when no numeric component remains.
    """
    try:
        parts = branch.strip().lower().split(".")
        numbers = tuple(int(part) for part in parts if part not in ("", "x"))
        return numbers if numbers else None
    except (ValueError, AttributeError):
        return None


def is_version_upgrade(source_branch: str, new_branch: str) -> bool:
    """Return True when ``new_branch`` is a numerically newer version.

    Returns False when either branch name is unparseable.
    """
    source_version = parse_minecraft_version(source_branch)
    target_version = parse_minecraft_version(new_branch)
    if source_version is None or target_version is None:
        return False
    return target_version > source_version


def prepare_new_version(args, root_path, project_path):
    """Clone ``args.name`` and create ``args.minecraft`` from ``args.init``.

    Aborts with ``error2`` when the local ``project_path`` already exists or
    the remote branch is already present; otherwise clones the repository,
    checks out the new branch from ``origin/<args.init>``, and pushes it with
    upstream tracking. For numeric upgrades only, the source branch's ``run``
    directory is copied into the new branch when it is absent.

    Args:
        args: Parsed CLI arguments (``name``, ``minecraft``, ``init``).
        root_path: Parent directory that receives the clone.
        project_path: Target directory of the new branch.

    Side effects: runs git subprocesses, may copy the ``run`` directory, and
    prints progress lines.
    """
    remote_url = f"git@github.com:Fuzss/{args.name}.git"
    new_branch = args.minecraft
    source_branch = args.init

    if os.path.isdir(project_path):
        warn2(f"Branch {new_branch} already exists, skipping")
        return

    result = subprocess.run(
        ["git", "ls-remote", "--heads", remote_url, new_branch],
        capture_output=True,
        text=True,
        check=True
    )

    if bool(result.stdout.strip()):
        error2(f"Failed to create new branch {new_branch}: branch already exists")

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
