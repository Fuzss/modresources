#!/usr/bin/env python3

"""
Clone and prepare version based git repositories.

- Reads versions.json from main repository
- Optionally creates it from defaults if missing
- Clones all enabled version branches into local folders
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
    """Check if a directory is a git repository."""
    return os.path.isdir(os.path.join(path, ".git"))


def clone_branch(repo_url: str, branch: str, target_dir: str, single_branch=False):
    """Clone a single branch into target directory."""
    subprocess.run([
        "git",
        "clone",
        "--branch", branch,
        *(["--single-branch"] if single_branch else []),
        repo_url,
        target_dir
    ], check=True
    )


def get_remote_branches(repo_dir: str) -> set[str]:
    """Return set of remote branch names.
    
    This only works when the repository has been cloned without the --single-branch flag.
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
    """
    Load or create versions.json and apply optional overrides.

    Also commits and pushes changes if file is created or modified.
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
                    print(f"Warning: Unkown support type {state}")
            else:
                branches.pop(version, None)

    with open(versions_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
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
        return False
    
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
    """Validate and return active version branches."""
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


def setup_git(root_path: str, repo_name: str):
    repo_url = f"{REMOTE_BASE_URL}{repo_name}.git"
    main_path = os.path.join(root_path, "main")

    os.makedirs(root_path, exist_ok=True)

    if is_git_repo(main_path):
        print("main already cloned, skipping")
    else:
        print(f"Cloning main branch into {main_path}")
        clone_branch(repo_url, "main", main_path)

    versions = load_versions(main_path)

    for version in versions:
        target_dir = os.path.join(root_path, version)

        if is_git_repo(target_dir):
            print(f"{version} already cloned, skipping")
            continue

        print(f"Cloning branch {version} into {target_dir}")
        clone_branch(repo_url, version, target_dir, single_branch=True)


def main():
    if len(sys.argv) != 2:
        print("Usage: clone_versions.py <repo-name>")
        sys.exit(1)

    repo_name = sys.argv[1]
    root_path = os.path.join(os.getcwd(), repo_name)

    setup_git(root_path, repo_name)


if __name__ == "__main__":
    main()
