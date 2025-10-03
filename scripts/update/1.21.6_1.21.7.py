import shutil
import sys
import os
import subprocess
import time

def update_properties(file_path, updates: dict):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    keys_handled = set()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or '=' not in line:
            new_lines.append(line)
            continue

        key, _ = line.split('=', 1)
        key = key.strip()
        if key in updates:
            new_value = updates[key]
            new_lines.append(f"{key}={new_value}\n")
            keys_handled.add(key)
        else:
            new_lines.append(line)

    with open(file_path, 'w') as f:
        f.writelines(new_lines)

def git_push_all(repo_path, project_name, commit_message):
    token = "github_pat_..."
    remote_url = f"https://{token}@github.com/Fuzss/{project_name}.git"
    commands = [
        ["git", "remote", "set-url", "origin", remote_url],
        ["git", "add", "."],
        ["git", "commit", "-m", commit_message],
        ["git", "push"]
    ]
    for cmd in commands:
        subprocess.run(cmd, cwd=repo_path, check=True)

def run_gradle_task(task, cwd, max_retries=3, timeout=150):
    cmd = ["./gradlew", task]
    attempt = 0

    while attempt < max_retries:
        try:
            print(f"Running Gradle task '{task}', attempt {attempt+1}/{max_retries}...")
            subprocess.run(cmd, cwd=cwd, timeout=timeout, check=True)
            return
        except subprocess.TimeoutExpired:
            print(f"Gradle task timed out after {timeout} seconds.")
        except subprocess.CalledProcessError as e:
            print(f"Gradle task failed with return code {e.returncode}.")
            print("Error output:\n", e.stderr)
        attempt += 1
        wait_time = 5
        print(f"Retrying in {wait_time} seconds...")
        time.sleep(wait_time)

    print("Gradle task failed after max retries.")

if len(sys.argv) < 2:
    print("Usage: python copy_override.py <source> <destination>")
    sys.exit(1)

project = sys.argv[1]
oldVersion = "1.21.6"
newVersion = "1.21.7"
basePath = f"/Users/user/Lokal/GitHub"
projectSource = f"{basePath}/{project}/{oldVersion}"
projectPath = f"{basePath}/{project}/{newVersion}"

gitIgnoreSource = f"{basePath}/multiloader-workspace-template/.gitignore"
gitIgnoreDestination = f"{basePath}/{project}/.gitignore"

if not os.path.isfile(gitIgnoreSource):
    print(f"Source file not found: {gitIgnoreSource}")
    sys.exit(1)

shutil.copy(gitIgnoreSource, gitIgnoreDestination)
print(f"Copied {gitIgnoreSource} → {gitIgnoreDestination}")

if os.path.isdir(projectSource):
    shutil.move(projectSource, projectPath)
    print(f"Moved {projectSource} → {projectPath}")

ideaPath = f"{projectPath}/.idea"
if os.path.isdir(ideaPath):
    shutil.rmtree(ideaPath)
    print(f"Removed {ideaPath}")

changelogSource = f"{basePath}/multiloader-workspace-template/{newVersion}/CHANGELOG.md"
changelogDestination = f"{projectPath}/CHANGELOG.md"

if not os.path.isfile(changelogSource):
    print(f"Source file not found: {changelogSource}")
    sys.exit(1)

shutil.copy(changelogSource, changelogDestination)
print(f"Copied {changelogSource} → {changelogDestination}")

newProperties = {
    "modVersion": "21.7.0",
    "dependenciesVersionCatalog": "1.21.7-v1",
    "dependenciesPuzzlesLibVersion": "21.7.0",
    "dependenciesMinPuzzlesLibVersion": "21.7.0"
}
update_properties(f"{projectPath}/gradle.properties", newProperties)
print(f"Updated properties {newProperties}")

neoforgeScript = """
tasks.withType(net.fabricmc.loom.task.AbstractRunTask).configureEach {
    doFirst {
        patchLaunchCfg()
    }
}
"""

with open(f"{projectPath}/NeoForge/build.gradle", "r+") as file:
    if "patchLaunchCfg()" not in file.read():
        file.write(neoforgeScript)

subprocess.run(["./gradlew", "commonGenSources"], cwd=projectPath, check=True)
subprocess.run(["./gradlew", "neoforgeData"], cwd=projectPath, check=True)
subprocess.run(["./gradlew", "allUploadEverywhere"], cwd=projectPath, check=True)
# run_gradle_task("fabricUploadCurseForge", projectPath)
# run_gradle_task("neoForgeUploadCurseForge", projectPath)
# run_gradle_task("fabricUploadModrinth", projectPath)
# run_gradle_task("neoForgeUploadModrinth", projectPath)

git_push_all(f"{basePath}/{project}", project, "full 1.21.7 port")
    