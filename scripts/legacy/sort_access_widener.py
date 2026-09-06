import sys
from pathlib import Path

OBJECT_TYPE_ORDER = {
    "class": 0,
    "field": 1,
    "method": 2
}

TRANSITIVE_CLASS_TWEAKER_ACCESS_LEVELS = {
    "transitive-accessible",
    "transitive-extendable",
    "transitive-mutable"
}

CLASS_TWEAKER_ACCESS_LEVELS = {
    "accessible",
    "extendable",
    "mutable",
    *TRANSITIVE_CLASS_TWEAKER_ACCESS_LEVELS,
}


def sort_key(line: str, access_levels: set[str] = CLASS_TWEAKER_ACCESS_LEVELS):
    stripped_line = line.strip()

    if not stripped_line or stripped_line.startswith("#"):
        return None

    parts = stripped_line.split()
    access_level = parts[0]

    if access_level not in access_levels:
        return None

    object_type = parts[1]
    class_name = parts[2]

    if object_type == "class":
        object_name = ""
        descriptor = ""
    else:
        object_name = parts[3]
        descriptor = parts[4] if len(parts) > 4 else ""

    return (
        class_name,
        OBJECT_TYPE_ORDER.get(object_type, 99),
        object_name,
        descriptor,
        access_level
    )


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 sort_access_widener.py <access_widener_path>")
        sys.exit(1)

    access_widener_path = Path(sys.argv[1])

    if not access_widener_path.is_file():
        print(f"File not found: {access_widener_path}")
        sys.exit(1)

    lines = access_widener_path.read_text(encoding="utf8").splitlines()

    transitive_lines = []
    sortable_lines = []

    for line in lines:
        if sort_key(line, TRANSITIVE_CLASS_TWEAKER_ACCESS_LEVELS):
            transitive_lines.append(line)
        elif sort_key(line, CLASS_TWEAKER_ACCESS_LEVELS):
            sortable_lines.append(line)

    transitive_lines.sort(key=sort_key)
    sortable_lines.sort(key=sort_key)

    sorted_lines = [
        "\t".join(line.split())
        for line in transitive_lines + sortable_lines
    ]

    access_widener_path.write_text(
        "\n".join(sorted_lines) + "\n",
        encoding="utf8"
    )
    

if __name__ == "__main__":
    main()