#!/usr/bin/env python3
"""Convert a ``mixins.json`` configuration into Gradle DSL mixin declarations.

Purpose: migrate legacy mixin configuration files to the multiloader Gradle
DSL during the 1.21.11 workspace upgrade.

Entry points: ``workspace_upgrade.run_1_21_11_upgrade``; the module also runs
standalone as
``python3 core/migrate_mixins.py <mixins.json> <build.gradle>``.

Side effects: appends a ``multiloader { mixins { ... } }`` block to the Gradle
file and prints usage on bad arguments.

Constraints: standard library only. Missing JSON files are ignored. The block
is appended, so the Gradle file must not already contain one.
"""

import json
import sys
import os

def split_mixins(entries, prefix="", accessor_prefix=""):
    """Split mixin class names into normal and accessor lists.

    ``$`` is escaped for Gradle string interpolation. Entries starting with
    ``accessor_prefix`` (or ``prefix``) have that prefix stripped before being
    placed in the corresponding list.

    Args:
        entries: Mixin class names from one section of ``mixins.json``.
        prefix: Optional package prefix for normal mixins.
        accessor_prefix: Optional package prefix for accessor mixins.

    Returns:
        A ``(normal, accessor)`` tuple of name lists.
    """
    normal = []
    accessor = []
    for entry in entries:
        entry = entry.replace("$", "\\$")
        if accessor_prefix and entry.startswith(accessor_prefix):
            accessor.append(entry[len(accessor_prefix):])
        elif prefix and entry.startswith(prefix):
            normal.append(entry[len(prefix):])
        else:
            normal.append(entry)
    return normal, accessor

def convert_mixins(json_path, gradle_path):
    """Append the mixin declarations from ``json_path`` to ``gradle_path``.

    Reads the ``mixins``, ``client``, and ``server`` sections plus the
    ``plugin`` class, then appends a ``multiloader { mixins { ... } }`` block
    for each non-empty group. Does nothing when the JSON file is missing or
    yields no declarations.

    Args:
        json_path: Legacy ``mixins.json`` file.
        gradle_path: Gradle DSL file the block is appended to.

    Side effects: reads the JSON file and appends to the Gradle file.
    """
    if not os.path.exists(json_path):
        return

    with open(json_path, "r", encoding="utf-8") as file:
        mixin_config = json.load(file)

    common_mixins, common_accessors = split_mixins(
        mixin_config.get("mixins", []),
        accessor_prefix="accessor."
    )

    client_mixins, client_accessors = split_mixins(
        mixin_config.get("client", []),
        "client.",
        "client.accessor."
    )

    server_mixins, server_accessors = split_mixins(
        mixin_config.get("server", []),
        "server.",
        "server.accessor."
    )

    lines = []

    plugin_class = mixin_config.get("plugin")
    if plugin_class:
        lines.append(f'        plugin.set("{plugin_class
                                            .replace("modGroup", "project.group")
                                            .replace("fabric", "${project.packageName}")
                                            .replace("neoforge", "${project.packageName}")
                                            }")')

    if common_mixins:
        joined = ", ".join(f'"{name}"' for name in common_mixins)
        lines.append(f"        mixin({joined})")

    if common_accessors:
        joined = ", ".join(f'"{name}"' for name in common_accessors)
        lines.append(f"        accessor({joined})")

    if client_mixins:
        joined = ", ".join(f'"{name}"' for name in client_mixins)
        lines.append(f"        clientMixin({joined})")

    if client_accessors:
        joined = ", ".join(f'"{name}"' for name in client_accessors)
        lines.append(f"        clientAccessor({joined})")

    if server_mixins:
        joined = ", ".join(f'"{name}"' for name in server_mixins)
        lines.append(f"        serverMixin({joined})")

    if server_accessors:
        joined = ", ".join(f'"{name}"' for name in server_accessors)
        lines.append(f"        serverAccessor({joined})")

    if lines:
        lines.insert(0, "")
        lines.insert(1, "multiloader {")
        lines.insert(2, "    mixins {")
        lines.append("    }")
        lines.append("}")
        lines.append("")

        with open(gradle_path, "a", encoding="utf-8") as file:
            file.write("\n".join(lines))

def main():
    """Run the standalone ``migrate_mixins.py`` entry point.

    Side effects: prints usage and exits with code 1 on bad arguments;
    otherwise converts the given files.
    """
    if len(sys.argv) != 3:
        print("Usage: python3 core/migrate_mixins.py <mixins.json> <build.gradle>")
        sys.exit(1)

    json_path = sys.argv[1]
    gradle_path = sys.argv[2]
    convert_mixins(json_path, gradle_path)

if __name__ == "__main__":
    main()
