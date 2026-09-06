#!/usr/bin/env python3
import json
import os

DEFAULTS = {
    "dependencies": {
        "fabricapi": "required",
        "forgeconfigapiport": "required",
        "puzzleslib": "required"
    },
    "environments": {
        "client": "required",
        "server": "required"
    },
    "loaders": [
        "fabric",
        "neoforge"
    ]
}

def prompt_distributions():
    distributions = {}
    for platform in ["curseforge", "github", "modrinth"]:
        print(f"Enter values for {platform}:")
        if platform in ["curseforge", "modrinth"]:
            id_val = input("  id: ").strip() or "0"
        slug_val = input("  slug: ").strip() or "0"

        entry = {"slug": slug_val}
        if platform in ["curseforge", "modrinth"]:
            entry["id"] = id_val
        distributions[platform] = entry
    return distributions

def main():
    while True:
        file_name = input("Enter mod id: ").strip()
        if file_name:
            break
        print("File name cannot be empty!")

    data = {
        "dependencies": DEFAULTS["dependencies"],
        "distributions": prompt_distributions(),
        "environments": DEFAULTS["environments"],
        "loaders": DEFAULTS["loaders"]
    }

    os.makedirs("output", exist_ok=True)
    path = os.path.join("..", "mods", f"{file_name}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=4)
    print(f"File saved to {path}")

if __name__ == "__main__":
    main()
