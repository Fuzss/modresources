#!/usr/bin/env python3
"""CLI argument parsing and JSON config merging.

Purpose: define the ``main.py`` command-line surface and overlay an optional
``config/<minecraft>/<name>.json`` file on the parsed arguments.

Entry points: ``main.parse_args`` is the only caller.

Side effects: reads a config JSON file when ``--config`` is given, prints the
final arguments as sorted JSON, and exits via ``error2`` for an unknown config
key or a missing config file.

Constraints: standard library only; the argparse definitions are the single
source of truth for the CLI surface. Run from ``scripts/main`` so the relative
``config/`` path resolves.
"""

import argparse
import json
from pathlib import Path

from console import error2


def merge_config_into_args(parser, args, config_data):
    """Overlay config values on arguments that still hold their default.

    Args:
        parser: Argument parser whose action defaults define "unset".
        args: Namespace to mutate in place.
        config_data: Parsed config mapping ``dest`` names to values.

    Side effects: mutates ``args``; exits via ``error2`` for an unknown key.
    """
    defaults = {
        action.dest: action.default
        for action in parser._actions
        if action.dest != "help"
    }

    for key, value in config_data.items():
        if key not in defaults:
            error2(f"Unknown config key: {key}")

        if getattr(args, key, None) == defaults.get(key):
            setattr(args, key, value)


def parse_args():
    """Parse ``sys.argv``, merge an optional config file, and return the namespace.

    ``--config <name>`` loads ``config/<--minecraft>/<name>.json``. When
    ``--id`` is omitted it is derived from ``--name`` by removing hyphens. The
    resolved arguments are printed as JSON before returning.

    Side effects: reads the config file, prints to stdout, and exits via
    ``error2`` for an unknown config key or a missing config file.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("--bare", default=False, action="store_true", help="Skip any Gradle setup.")
    parser.add_argument("--branch", default=[], action="append", nargs=2, metavar=("BRANCH_NAME", "SUPPORT_STATUS"), help="Updates branch status in versions.json, can be used multiple times. Format: --branch <branch_name> <support_status>")
    parser.add_argument("--catalog", type=str, default=None, metavar="VERSION_CATALOG", help="Version-based catalog. Example: --catalog 26.2-SNAPSHOT")
    parser.add_argument("--changelog", default=None, action="append", nargs=2, metavar=("SECTION_NAME", "TEXT"), help="Add a changelog line, can be used multiple times. Format: --changelog <section_name> <text>")
    parser.add_argument("--commit", default=False, action="store_true", help="Commit to GitHub.")
    parser.add_argument("--config", type=str, metavar="CONFIG_NAME", help="Args as JSON config file. Example: --config upgrade-upload")
    parser.add_argument("--data", default=False, action="store_true", help="Generate data.")
    parser.add_argument("--gradle", type=str, default=None, metavar="GRADLE_VERSION", help="Gradle wrapper version. Example: --gradle 9.6.0")
    parser.add_argument("--id", type=str, default=None, metavar="MOD_ID", help="Mod id. Example: --id examplemod")
    parser.add_argument("--init", nargs="?", const=True, default=None, metavar="SOURCE_BRANCH", help="Setup git repository and version branch, with optional argument. Example: --init [26.2.x]")
    parser.add_argument("--launch", default=[], action="append", nargs="*", metavar=("MOD_LOADER", "DISTRIBUTION"), help="Launch the game, can be used multiple times. Format: --launch <mod_loader> <distribution>")
    parser.add_argument("--legacy", nargs="?", const=True, default=None, metavar="SCOPE", help="Use legacy Gradle property and task names. Format: --legacy <scope>")
    parser.add_argument("--minecraft", type=str, required=True, metavar="MINECRAFT_VERSION", help="Minecraft name. Example: --minecraft 26.2.x")
    parser.add_argument("--name", type=str, required=True, metavar="REPOSITORY_NAME", help="Repository name. Example: --name example-mod")
    parser.add_argument("--notify", default=False, action="store_true", help="Notify via Discord webhook.")
    parser.add_argument("--open", default=None, nargs="*", metavar="ENVIRONMENT", help="Open in Finder, or Idea. Format: --open <environment>")
    parser.add_argument("--path", type=str, default=None, metavar="ROOT_PATH", help="Override default root path. Example: --path /absolute/path/to/project")
    parser.add_argument("--plugins", type=str, default=None, metavar="PLUGINS_VERSION", help="Multiloader convention plugins version. Example: --plugins 1.1-SNAPSHOT")
    parser.add_argument("--properties", default=None, action="append", nargs=2, metavar=("KEY", "VALUE"), help="Set a gradle.properties value, can be used multiple times. Format: --properties <key> <value>")
    parser.add_argument("--publish", default=False, action="store_true", help="Publish to Maven.")
    parser.add_argument("--spotless", type=str, default=None, metavar="TASK_NAME", help="Run spotless upgrade tasks for a specific game update. Example: --spotless tinytakeover")
    parser.add_argument("--upgrade", nargs="?", const=True, default=None, metavar="PATCHES_NAME", help="Run workspace upgrade, potentially for a specific version, with optional argument. Example: --upgrade [26.1.x]")
    parser.add_argument("--upload", default=None, nargs="*", metavar=("MOD_LOADER", "WEBSITE"), help="Upload to CurseForge, Modrinth, or GitHub. Format: --upload <mod_loader> <website>")
    parser.add_argument("--version", type=str, default=None, metavar="PROJECT_VERSION", help="Mod version. Example: --version 26.2.0")

    args = parser.parse_args()

    if args.config:
        config_path = Path("config") / args.minecraft / f"{args.config}.json"
        if config_path.is_file():
            config_data = json.loads(config_path.read_text())
            merge_config_into_args(parser, args, config_data)
        else:
            error2(f"Config not found at {config_path}")

    if not args.id:
        args.id = args.name.replace("-", "")

    print(json.dumps(vars(args), indent=2, sort_keys=True))

    return args
