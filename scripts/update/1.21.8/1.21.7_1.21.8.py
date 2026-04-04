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
oldVersion = "1.21.7"
newVersion = "1.21.8"
modVersion = "21.8.0"
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

githubSource = f"{basePath}/multiloader-workspace-template/.github"
githubDestination = f"{basePath}/{project}/.github"

if not os.path.isdir(githubSource):
    print(f"Source directory not found: {githubSource}")
    sys.exit(1)

if os.path.exists(githubDestination):
    shutil.rmtree(githubDestination)

shutil.copytree(githubSource, githubDestination)
print(f"Copied {githubSource} → {githubDestination}")

if os.path.isdir(projectSource):
    shutil.move(projectSource, projectPath)
    print(f"Moved {projectSource} → {projectPath}")

ideaPath = f"{projectPath}/.idea"
if os.path.isdir(ideaPath):
    shutil.rmtree(ideaPath)
    print(f"Removed {ideaPath}")

gradlePath = f"{projectPath}/.gradle"
if os.path.isdir(gradlePath):
    shutil.rmtree(gradlePath)
    print(f"Removed {gradlePath}")

git_push_all(f"{basePath}/{project}", project, f"prepare {newVersion} port")

changelogSource = f"{basePath}/multiloader-workspace-template/{newVersion}/CHANGELOG.md"
changelogDestination = f"{projectPath}/CHANGELOG.md"

if not os.path.isfile(changelogSource):
    print(f"Source file not found: {changelogSource}")
    sys.exit(1)

shutil.copy(changelogSource, changelogDestination)
print(f"Copied {changelogSource} → {changelogDestination}")

newProperties = {
    "modVersion": modVersion,
    "dependenciesVersionCatalog": f"{newVersion}-v1",
    "dependenciesPuzzlesLibVersion": modVersion,
    "dependenciesMinPuzzlesLibVersion": modVersion
}
update_properties(f"{projectPath}/gradle.properties", newProperties)
print(f"Updated ./gradle.properties: {newProperties}")

neoforgeScriptBlock = """
tasks.withType(net.fabricmc.loom.task.AbstractRunTask).configureEach {
    doFirst {
        patchLaunchCfg()
    }
}
"""

neoforgeScriptPath = f"{projectPath}/NeoForge/build.gradle"
with open(neoforgeScriptPath, "r") as file:
    content = file.read()

newContent = content.replace(neoforgeScriptBlock, "")
if content != newContent:
    with open(neoforgeScriptPath, "w") as file:
        file.write(newContent)

print("Updated ./NeoForge/build.gradle")

print("Generating common sources...")
subprocess.run(["./gradlew", "commonGenSources"], cwd=projectPath, check=True)

propertiesScriptBlock = """
# Optional Dependencies
dependenciesOptionalFabricCurseForge=config-menus-forge
dependenciesOptionalNeoForgeCurseForge=config-menus-forge
dependenciesOptionalForgeCurseForge=config-menus-forge
dependenciesOptionalFabricModrinth=forge-config-screens
dependenciesOptionalNeoForgeModrinth=forge-config-screens
dependenciesOptionalForgeModrinth=forge-config-screens
"""

propertiesScriptPath = f"{projectPath}/gradle.properties"
with open(propertiesScriptPath, "r") as file:
    content = file.read()

newContent = content.replace(propertiesScriptBlock, "")
if content != newContent:
    with open(propertiesScriptPath, "w") as file:
        file.write(newContent)
else:
    print(f"Optional dependencies block not found")
    sys.exit(1)

print("Updated gradle.properties")

print("Running data generation...")
subprocess.run(["./gradlew", "neoforgeData"], cwd=projectPath, check=True)

if sys.argv[2] != "skipUpload=true":
    print("Uploading everywhere...")
    subprocess.run(["./gradlew", "allUploadEverywhere"], cwd=projectPath, check=True)

# run_gradle_task("fabricUploadCurseForge", projectPath)
# run_gradle_task("neoForgeUploadCurseForge", projectPath)
# run_gradle_task("fabricUploadModrinth", projectPath)
# run_gradle_task("neoForgeUploadModrinth", projectPath)

git_push_all(f"{basePath}/{project}", project, f"full {newVersion} port")
    