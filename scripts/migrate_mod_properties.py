#!/usr/bin/env python3
import sys

# Environment mapping
ENV_MAPPING = {
    "IGNORE_ALL_VERSION": ("required", "unsupported"),
    "IGNORE_SERVER_VERSION": ("unsupported", "required"),
    "MATCH_VERSION": ("required", "required")
}

# Helper functions
def slugify(name):
    return name.lower().replace(" ", "-")

def parse_old_properties(file_path):
    props = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                props[key.strip()] = value.strip()
    return props

def convert_slug_to_id(name: str):
    id = name.strip().replace("-", "").lower()
    if id == "forgeconfigapiportfabric":
        return "forgeconfigapiport"
    else:
        return id

def convert_dependencies(props):
    new_deps = {}
    dep_map = {
        "dependenciesRequiredFabricCurseForge": ("fabric", "required"),
        "dependenciesRequiredFabricModrinth": ("fabric", "required"),
        "dependenciesEmbeddedFabricCurseForge": ("fabric", "embedded"),
        "dependenciesEmbeddedFabricModrinth": ("fabric", "embedded"),
        "dependenciesOptionalFabricCurseForge": ("fabric", "optional"),
        "dependenciesOptionalFabricModrinth": ("fabric", "optional"),
        "dependenciesRequiredNeoForgeCurseForge": ("neoforge", "required"),
        "dependenciesRequiredNeoForgeModrinth": ("neoforge", "required"),
        "dependenciesEmbeddedNeoForgeCurseForge": ("neoforge", "embedded"),
        "dependenciesEmbeddedNeoForgeModrinth": ("neoforge", "embedded"),
        "dependenciesOptionalNeoForgeCurseForge": ("neoforge", "optional"),
        "dependenciesOptionalNeoForgeModrinth": ("neoforge", "optional")
    }

    for old_key, platform in dep_map.items():
        if old_key in props:
            dependencies = [convert_slug_to_id(dependency) for dependency in props[old_key].split(",")]
            for dependency in dependencies:
                key = f"dependencies.{platform[0]}.{dependency}"
                new_deps[key] = platform[1]

    # Sort the dictionary by key
    new_deps = dict(sorted(new_deps.items()))
    return new_deps

def convert_distributions(props):
    result = {}
    mod_name_slug = slugify(props.get("modName", "mod"))
    github_slug = props.get("modSourceUrl", "").rstrip("/").split("/")[-1]

    curseforge_id = props.get("projectCurseForgeId", "")
    if curseforge_id and curseforge_id != "0":
        result["distributions.curseforge.id"] = curseforge_id
        result["distributions.curseforge.slug"] = mod_name_slug

    if github_slug:
        result["distributions.github.slug"] = github_slug

    modrinth_id = props.get("projectModrinthId", "")
    if modrinth_id and modrinth_id != "0":
        result["distributions.modrinth.id"] = modrinth_id
        result["distributions.modrinth.slug"] = mod_name_slug

    return result

def migrate_properties(input_file, output_file):
    props = parse_old_properties(input_file)

    if "dependenciesVersionCatalog" not in props:
        print(f"Nothing to migrate in {input_file}")
        return

    with open(output_file, "w", encoding="utf-8") as file:
        file.write("org.gradle.caching=true\n")
        file.write("org.gradle.configuration-cache=false\n")
        file.write("org.gradle.daemon=true\n")
        file.write("org.gradle.jvmargs=-Xmx2G\n")
        file.write("org.gradle.parallel=true\n")
        file.write("loom.ignoreDependencyLoomVersionValidation=true\n\n")
        old_version = props.get("dependenciesVersionCatalog")  # e.g., "1.21.10-v1"
        base_version = old_version.split("-")[0]  # "1.21.10"
        new_version = f"{base_version}-SNAPSHOT"  # "1.21.10-SNAPSHOT"
        file.write(f"project.libs={new_version}\n")
        file.write("project.platforms=Common, Fabric, NeoForge\n")
        file.write("project.plugins=1.0-SNAPSHOT\n\n")
        
        file.write(f"mod.authors={props.get('modAuthor', '')}\n")
        file.write(f"mod.description={props.get('modDescription', '')}\n")
        file.write(f"mod.group={props.get('modMavenGroup', '')}\n")
        file.write(f"mod.id={props.get('modId', '')}\n")
        file.write(f"mod.license={props.get('modLicense', '')}\n")
        file.write(f"mod.name={props.get('modName', '')}\n")
        file.write(f"mod.version={props.get('modVersion', '')}\n\n")
        
        deps = convert_dependencies(props)
        for k, v in deps.items():
            file.write(f"{k}={v}\n")
        if deps:
            file.write("\n")
        
        dists = convert_distributions(props)
        for k, v in dists.items():
            file.write(f"{k}={v}\n")
        if dists:
            file.write("\n")
        
        env_client, env_server = ENV_MAPPING.get(props.get("modForgeDisplayTest", "MATCH_VERSION"), ("required", "required"))
        file.write(f"environments.client={env_client}\n")
        file.write(f"environments.server={env_server}\n")

    print(f"Successfully migrated properties in {input_file}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 convert_gradle.py <input_file> <output_file>")
        sys.exit(1)

    migrate_properties(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
