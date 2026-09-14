#!/usr/bin/env python3
"""Migrate a legacy ``gradle.properties`` layout to the current property names.

Purpose: rewrite the old flat property file (individual dependency and
distribution keys) as the current ``mod.*``, ``dependencies.*``,
``distributions.*``, and ``environments.*`` layout during workspace upgrades.

Entry points: ``workspace_upgrade.run_1_21_11_upgrade``; the module also runs
standalone as
``python3 migrate_mod_properties.py <input> <output> <plugins_version>``.

Side effects: overwrites the output file, prints progress, and exits via
``error2`` when the plugins version is missing.

Constraints: standard library only. An input without
``dependenciesVersionCatalog`` is treated as already migrated and left alone.
"""

import sys

from console import error2

# Maps legacy modForgeDisplayTest values to (client, server) support statuses.
ENV_MAPPING = {
    "IGNORE_ALL_VERSION": ("required", "unsupported"),
    "IGNORE_SERVER_VERSION": ("unsupported", "required"),
    "MATCH_VERSION": ("required", "required")
}

def slugify(name):
    """Return ``name`` lowercased with spaces replaced by hyphens."""
    return name.lower().replace(" ", "-")

def parse_old_properties(file_path):
    """Return ``file_path`` as a ``{key: value}`` dict, skipping blanks/comments."""
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
    """Return the mod ID for a distribution slug.

    Lowercases, removes hyphens, and normalizes the special
    ``forgeconfigapiportfabric`` slug to ``forgeconfigapiport``.
    """
    mod_id = name.strip().replace("-", "").lower()
    if mod_id == "forgeconfigapiportfabric":
        return "forgeconfigapiport"
    else:
        return mod_id

def convert_dependencies(props):
    """Convert legacy dependency keys into ``dependencies.<loader>.<id>`` entries.

    Args:
        props: Parsed legacy properties.

    Returns:
        A key-sorted ``{dependencies.<loader>.<id>: required|optional|embedded}``
        dict.
    """
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
    new_deps = dict(sorted(new_deps.items()))
    return new_deps

def convert_distributions(props):
    """Convert legacy distribution keys into ``distributions.<site>.*`` entries.

    CurseForge and Modrinth IDs are emitted only when present and non-zero;
    each present site also receives the mod name slug.

    Args:
        props: Parsed legacy properties.

    Returns:
        A ``{distributions.<site>.<field>: value}`` dict.
    """
    result = {}
    mod_name_slug = slugify(props.get("modName", "mod"))

    curseforge_id = props.get("projectCurseForgeId", "")
    if curseforge_id and curseforge_id != "0":
        result["distributions.curseforge.id"] = curseforge_id
        result["distributions.curseforge.slug"] = mod_name_slug

    github_url = props.get("modSourceUrl", "")
    if github_url:
        result["distributions.github.slug"] = mod_name_slug

    modrinth_id = props.get("projectModrinthId", "")
    if modrinth_id and modrinth_id != "0":
        result["distributions.modrinth.id"] = modrinth_id
        result["distributions.modrinth.slug"] = mod_name_slug

    return result

def migrate_properties(input_file, output_file, plugins_version):
    """Rewrite a legacy property file at ``output_file``.

    Returns early when the input has no ``dependenciesVersionCatalog`` (already
    migrated). The catalog ``x.y.z-vN`` becomes ``x.y.z-SNAPSHOT``, and the
    legacy display-test flag maps to the client and server environment support
    statuses.

    Args:
        input_file: Legacy properties file to read.
        output_file: Properties file to overwrite.
        plugins_version: Multiloader convention plugins version.

    Side effects: overwrites ``output_file`` and prints progress; exits via
    ``error2`` when ``plugins_version`` is missing.
    """
    props = parse_old_properties(input_file)

    if "dependenciesVersionCatalog" not in props:
        print(f"Nothing to migrate in {input_file}")
        return

    if not plugins_version:
        error2("Missing plugins version for gradle.properties migration")

    with open(output_file, "w", encoding="utf-8") as file:
        file.write("org.gradle.caching=true\n")
        file.write("org.gradle.configuration-cache=false\n")
        file.write("org.gradle.daemon=true\n")
        file.write("org.gradle.jvmargs=-Xmx4G\n")
        file.write("org.gradle.parallel=true\n")
        file.write("loom.ignoreDependencyLoomVersionValidation=true\n\n")
        old_version = props.get("dependenciesVersionCatalog")  # e.g., "1.21.10-v1"
        base_version = old_version.split("-")[0]  # "1.21.10"
        new_version = f"{base_version}-SNAPSHOT"  # "1.21.10-SNAPSHOT"
        file.write(f"project.libs={new_version}\n")
        file.write("project.platforms=Common, Fabric, NeoForge\n")
        file.write(f"project.plugins={plugins_version}\n\n")
        
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
    """Run the standalone ``migrate_mod_properties.py`` entry point.

    Side effects: prints usage and exits with code 1 on bad arguments;
    otherwise migrates the given files.
    """
    if len(sys.argv) != 4:
        print("Usage: python3 migrate_mod_properties.py <input_file> <output_file> <plugins_version>")
        sys.exit(1)

    migrate_properties(sys.argv[1], sys.argv[2], sys.argv[3])

if __name__ == "__main__":
    main()
