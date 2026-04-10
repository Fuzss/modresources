#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

REMOTE_BASE_URL = "https://github.com/Fuzss/"
DEFAULT_BRANCHES = {
        "1.21.11": "primary",
        "1.21.1": "maintained",
        "1.20.1": "fixes"
    }

VERSIONS_FILE = "versions.json"


def run(command, cwd=None, capture=False):
    if capture:
        return subprocess.check_output(command, cwd=cwd, text=True).strip()
    subprocess.run(command, cwd=cwd, check=True)


def is_git_repo(path):
    return (path / ".git").exists()


def clone_branch(repo_url, branch, target_dir):
    run([
        "git",
        "clone",
        "--branch", branch,
        repo_url,
        str(target_dir)
    ])


def get_remote_branches(repo_dir):
    output = run(
        ["git", "branch", "-r"],
        cwd=repo_dir,
        capture=True
    )

    branches = set()
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("origin/"):
            name = line.removeprefix("origin/")
            if name != "HEAD":
                branches.add(name)

    return branches


def load_versions_file(main_path, versions_file, branch_overrides=None):
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

    for version, state in (branch_overrides or {}).items():
        if state:
            branches[version] = state
        else:
            branches.pop(version, None)

    with versions_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    run(["git", "add", VERSIONS_FILE], cwd=main_path)
    run(["git", "commit", "-m", "Add default versions.json"], cwd=main_path)
    run(["git", "push", "origin", "main"], cwd=main_path)

    return data


def load_versions(main_path):
    versions_file = main_path / VERSIONS_FILE
    
    data = load_versions_file(main_path, versions_file)
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


def setup_git(root_path, repo_name):
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
