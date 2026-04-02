#!/usr/bin/env python3
import subprocess
import re
from pathlib import Path
import os
import sys

def run_command(command, check=True, capture_output=False, text=True):
    """Run a shell command and return result if requested."""
    return subprocess.run(command, check=check, capture_output=capture_output, text=text)

def check_remote_branches(version_dirs, remote_url):
    """Check if any version directories already have a branch on the remote."""
    existing = []
    for version in version_dirs:
        result = run_command(["git", "ls-remote", "--heads", remote_url, version], capture_output=True)
        if result.stdout.strip():
            existing.append(version)
    return existing

def create_version_branch(version, remote_url):
    """Create a branch for a version directory, push it, and remove it from main."""
    print(f"\nProcessing main {version} -> branch {version}")

    # Delete local branch if exists
    run_command(["git", "branch", "-D", version], check=False)

    # Checkout main and create branch
    run_command(["git", "checkout", "main"])
    run_command(["git", "checkout", "-b", version])

    # Filter branch: keep version dir + shared files, move version contents to root
    run_command([
        "git", "filter-repo",
        "--subdirectory-filter", f"{version}/",
        "--path", "README.md",
        "--path", ".gitignore",
        "--force"
    ])

    # Re-add remote (filter-repo removes it)
    run_command(["git", "remote", "add", "origin", remote_url], check=False)

    # Push branch to origin
    run_command(["git", "push", "origin", version, "--force"])

    # Reset main to clean state
    run_command(["git", "fetch", "origin"])
    run_command(["git", "checkout", "main"])
    run_command(["git", "reset", "--hard", "origin/main"])
    run_command(["git", "clean", "-fdx"])

def remove_versions_from_main(version_dirs, remote_url):
    print(f"\nRemoving versions from main {version_dirs}")

    args = ["git", "filter-repo"]
    for version in version_dirs:
        args.extend(["--path", f"{version}/"])

    args.extend(["--invert-paths", "--force"])

    run_command(args)

    # Re-add remote after filter-repo removes it
    run_command(["git", "remote", "add", "origin", remote_url], check=False)

    # Push the rewritten main to remote
    run_command(["git", "push", "origin", "main", "--force"])

    # Ensure main is clean locally
    run_command(["git", "fetch", "origin"])
    run_command(["git", "checkout", "main"])
    run_command(["git", "reset", "--hard"])
    run_command(["git", "clean", "-fdx"])

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 split_versions.py <repo-url>")
        sys.exit(1)

    remote_url = sys.argv[1]
    repo_path = Path.cwd()

    # Clone repo if not already cloned
    print(f"Cloning repository {remote_url}...")
    run_command(["git", "clone", remote_url])
    
    # Determine repo folder name from URL
    repo_name = remote_url.rstrip("/").split("/")[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    repo_path = repo_path / repo_name

    # Change working directory into the repo
    os.chdir(repo_path)

    # Pattern for version directories
    version_pattern = re.compile(r"^\d+\.\d+\.(\d+|x)$")

    # Find all version directories
    version_dirs = [d.name for d in repo_path.iterdir() if d.is_dir() and version_pattern.match(d.name)]
    if not version_dirs:
        print("No version directories found matching pattern \\d+.\\d+.\\d+")
        sys.exit(0)

    # Safety check: ensure no remote branch exists for any version
    print("Checking for existing version branches on remote...")
    existing_branches = check_remote_branches(version_dirs, remote_url)
    if existing_branches:
        print("Error: The following version branches already exist on the remote:")
        for branch in existing_branches:
            print(f"  - {branch}")
        print("\nPlease resolve manually before running the script.")
        sys.exit(1)

    # Process each version
    for version in version_dirs:
        create_version_branch(version, remote_url)

    remove_versions_from_main(version_dirs, remote_url)

    print("\nAll version branches processed, pushed, and removed from main.")

if __name__ == "__main__":
    main()
