#!/usr/bin/env python3

"""
Clone and prepare version based git repositories.

- Reads versions.json from main repository
- Optionally creates it from defaults if missing
- Clones all enabled version branches into local folders
"""

import json
import subprocess
import sys
from pathlib import Path


REMOTE_BASE_URL = "https://github.com/Fuzss/"
VERSIONS_FILE = "versions.json"

SUPPORT_TYPES = ["primary", "maintained", "fixes", "archived"]
DEFAULT_BRANCHES = {
    "1.21.11": "primary",
    "1.21.1": "maintained",
    "1.20.1": "fixes"
}


def is_git_repo(path: Path) -> bool:
    """Check if a directory is a git repository."""
    return (path / ".git").exists()


def clone_branch(repo_url: str, branch: str, target_dir: Path):
    """Clone a single branch into target directory."""
    subprocess.run([
        "git",
        "clone",
        "--branch", branch,
        repo_url,
        str(target_dir)
    ], check=True)


def get_remote_branches(repo_dir: Path) -> set[str]:
    """Return set of remote branch names."""
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


def load_versions_file(main_path: Path, branch_overrides=None):
    """
    Load or create versions.json and apply optional overrides.

    Also commits and pushes changes if file is created or modified.
    """

    versions_file = main_path / VERSIONS_FILE
    data = {}

    if versions_file.exists():
        with versions_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

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

    with versions_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    subprocess.run(
        ["git", "add", versions_file.name],
        cwd=main_path
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


def load_versions(main_path: Path):
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


def setup_git(root_path: Path, repo_name: str):
    """Clone main repo and all enabled version branches."""
    repo_url = f"{REMOTE_BASE_URL}{repo_name}.git"
    main_path = root_path / "main"

    root_path.mkdir(parents=True, exist_ok=True)

    if is_git_repo(main_path):
        print("main already cloned, skipping")
    else:
        print(f"Cloning main branch into {main_path}")
        clone_branch(repo_url, "main", main_path)

    versions = load_versions(main_path)

    for version in versions:
        target_dir = root_path / version

        if is_git_repo(target_dir):
            print(f"{version} already cloned, skipping")
            continue

        print(f"Cloning branch {version} into {target_dir}")
        clone_branch(repo_url, version, target_dir)


def main():
    if len(sys.argv) != 2:
        print("Usage: clone_versions.py <repo-name>")
        sys.exit(1)

    repo_name = sys.argv[1]
    root_path = Path.cwd() / repo_name

    setup_git(root_path, repo_name)


if __name__ == "__main__":
    main()
