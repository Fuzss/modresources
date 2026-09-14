#!/usr/bin/env python3

"""Clone and prepare version-based git repositories.

Purpose: bootstrap a project checkout from the remote repository: clone the
``main`` branch, read or create ``versions.json``, and clone each enabled
version branch into its own sibling directory.

Entry points: ``main.py`` imports ``setup_git`` and ``load_versions_file``;
the module also runs standalone as
``python3 core/clone_versions.py <repo-name>``.

Side effects: runs ``git`` subprocesses (pull, clone, fetch, branch, add,
commit, push) and writes ``versions.json``.

Constraints: standard library only. ``load_versions`` requires a clone with
fetched remote branches, not ``--single-branch``.
"""

import json
import os
import subprocess
import sys


REMOTE_BASE_URL = "https://github.com/Fuzss/"
VERSIONS_FILE = "versions.json"

SUPPORT_TYPES = ["primary", "maintained", "fixes", "archived"]
DEFAULT_BRANCHES = {
    "1.21.11": "primary",
    "1.21.1": "maintained",
    "1.20.1": "fixes"
}


def is_git_repo(path: str) -> bool:
    """Return True when ``path`` contains a ``.git`` directory."""
    return os.path.isdir(os.path.join(path, ".git"))


def clone_branch(repo_url: str, branch: str, target_dir: str):
    """Clone ``branch`` of ``repo_url`` into ``target_dir``, then fetch all refs.

    Side effects: runs ``git clone`` and ``git fetch --all``.
    """
    subprocess.run([
        "git",
        "clone",
        "--branch", branch,
        repo_url,
        target_dir
    ], check=True
    )

    subprocess.run([
        "git",
        "fetch",
        "--all"
    ], cwd=target_dir, check=True
    )


def get_remote_branches(repo_dir: str) -> set[str]:
    """Return the set of remote branch names in ``repo_dir``.

    ``origin/HEAD`` is excluded. Only works when the repository was cloned
    without ``--single-branch``.

    Side effects: runs ``git branch -r``.
    """
    output = subprocess.check_output(
        ["git", "branch", "-r"], 
        cwd=repo_dir, 
        text=True
    ).strip()

    branches = set()

    for line in output.splitlines():
        line = line.strip()

        if not line.startswith("origin/"):
            continue

        name = line.removeprefix("origin/")

        if name != "HEAD":
            branches.add(name)

    return branches


def load_versions_file(main_path: str, branch_overrides=None):
    """Load or create ``versions.json`` and apply optional support overrides.

    Pulls ``main_path`` first. A missing file is created from
    ``DEFAULT_BRANCHES``, keeping only branches that exist remotely. Each
    ``branch_overrides`` entry sets a support status (an unknown status is
    ignored with a warning) or removes the branch when its value is empty.
    The file is committed and pushed only when it changed.

    Args:
        main_path: The cloned ``main`` repository.
        branch_overrides: Optional ``{branch: support_status}`` mapping.

    Returns:
        The full parsed versions data, including its ``branches`` mapping.

    Side effects: runs git subprocesses (pull, add, diff, commit, push) and
    writes ``versions.json``.
    """

    versions_file = os.path.join(main_path, VERSIONS_FILE)
    data = {}

    subprocess.run(
        ["git", "pull"],
        cwd=main_path,
        check=True
    )

    if os.path.isfile(versions_file):
        with open(versions_file, "r", encoding="utf-8") as file:
            data = json.load(file)

    if data:
        if not branch_overrides:
            return data

    else:
        print("versions.json missing, creating from defaults")

        remote_branches = get_remote_branches(main_path)

        filtered_branches = {
            version: state
            for version, state in DEFAULT_BRANCHES.items()
            if version in remote_branches
        }

        data = {"branches": filtered_branches}

    branches = data.setdefault("branches", {})

    if branch_overrides:
        for version, state in branch_overrides.items():
            if state:
                state = state.strip().lower()
                if state in SUPPORT_TYPES:
                    branches[version] = state
                else:
                    print(f"Warning: Unknown support type {state}")
            else:
                branches.pop(version, None)

    with open(versions_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, sort_keys=True)
        file.write("\n")

    subprocess.run(
        ["git", "add", os.path.basename(versions_file)],
        cwd=main_path,
        check=True
    )

    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=main_path
    )

    if result.returncode == 0:
        print("No changes to commit, skipping commit and push.")
        return data
    
    subprocess.run(
        ["git", "commit", "-m", "Update versions.json"],
        cwd=main_path,
        check=True
    )

    subprocess.run(
        ["git", "push"],
        cwd=main_path,
        check=True
    )

    return data


def load_versions(main_path: str):
    """Return the non-archived version branches declared in ``versions.json``.

    Raises:
        RuntimeError: when a declared branch is absent from the remote.

    Side effects: reloads ``versions.json`` and lists remote branches.
    """
    data = load_versions_file(main_path)
    versions = data.get("branches", {})

    remote_branches = get_remote_branches(main_path)

    missing = [v for v in versions if v not in remote_branches]
    if missing:
        raise RuntimeError(
            f"versions.json references missing branches: {', '.join(missing)}"
        )

    return [
        version
        for version, state in versions.items()
        if state != "archived"
    ]


def setup_git(root_path: str, repo_name: str, versions_override: list[str] | None = None):
    """Clone the ``main`` branch and each enabled version branch.

    ``main`` is cloned when missing. The version list comes from
    ``versions_override`` when supplied, otherwise from ``load_versions``.
    Existing checkouts are left untouched.

    Args:
        root_path: Directory that receives the project clones.
        repo_name: Repository name under the ``Fuzss`` owner.
        versions_override: Explicit version branches to clone.

    Side effects: creates directories and runs ``git clone``/``git fetch``.
    """
    repo_url = f"{REMOTE_BASE_URL}{repo_name}.git"
    main_path = os.path.join(root_path, "main")

    os.makedirs(root_path, exist_ok=True)

    if is_git_repo(main_path):
        print("main already cloned, skipping")
    else:
        print(f"Cloning main branch into {main_path}")
        clone_branch(repo_url, "main", main_path)

    versions = versions_override or load_versions(main_path)

    for version in versions:
        target_dir = os.path.join(root_path, version)

        if is_git_repo(target_dir):
            print(f"{version} already cloned, skipping")
            continue

        print(f"Cloning branch {version} into {target_dir}")
        clone_branch(repo_url, version, target_dir)


def main():
    """Run the standalone ``clone_versions.py <repo-name>`` entry point.

    Side effects: clones repositories under a directory named after the
    repository in the current working directory.
    """
    if len(sys.argv) != 2:
        print("Usage: clone_versions.py <repo-name>")
        sys.exit(1)

    repo_name = sys.argv[1]
    root_path = os.path.join(os.getcwd(), repo_name)

    setup_git(root_path, repo_name)


if __name__ == "__main__":
    main()
