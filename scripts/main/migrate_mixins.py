#!/usr/bin/env python3
import json
import sys
import os

def split_mixins(entries, prefix="", accessor_prefix=""):
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
        lines.append(f'        plugin.set("{plugin_class}")')

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
    if len(sys.argv) != 3:
        print("Usage: python3 migrate_mixins.py <mixins.json> <build.gradle>")
        sys.exit(1)

    json_path = sys.argv[1]
    gradle_path = sys.argv[2]
    convert_mixins(json_path, gradle_path)

if __name__ == "__main__":
    main()
