#!/usr/bin/env zsh

cd "$(dirname "$0")/data" || exit 1

fallback="../commons/sections.yaml"

normalize() {
    # Remove empty lines (including lines containing only whitespace)
    sed '/^[[:space:]]*$/d'
}

fallback_content=$(normalize < "$fallback")

find . -type f -name "sections.yaml" | while read -r file; do
    [[ "$file" == "$fallback" ]] && continue

    if [[ "$(normalize < "$file")" == "$fallback_content" ]]; then
        echo "Removing $file (matches fallback ignoring empty lines)"
        rm "$file"
    fi
done
