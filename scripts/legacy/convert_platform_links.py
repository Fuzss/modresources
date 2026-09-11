#!/usr/bin/env python3
"""
Convert CurseForge and Modrinth links in Markdown files to platform aware
reference links.

The script searches every mod directory inside the supplied pages data
directory.

Only the following Markdown files are processed for each mod:

    configuration.md
    about.md
    features.md

For each matching file, it performs the following steps:

1. Reads the Markdown file.

2. Searches for inline Markdown links whose URLs start with one of the
   supported platform base URLs:

   https://www.curseforge.com/
   https://legacy.curseforge.com/
   https://modrinth.com/

3. Converts legacy CurseForge URLs to the current CurseForge URL by replacing
   only the URL base:

   https://legacy.curseforge.com/
       ->
   https://www.curseforge.com/

4. Derives a reference name from the final component of the URL path.

   For example:

   https://www.curseforge.com/minecraft/mc-mods/easy-shulker-boxes

   becomes:

   easy-shulker-boxes

   Non-word characters are replaced with dashes, and the result is converted
   to lowercase.

5. Replaces each supported inline link with an explicit Markdown reference
   link.

   For example:

   [Easy Shulker Boxes](https://www.curseforge.com/minecraft/mc-mods/easy-shulker-boxes)

   becomes:

   [Easy Shulker Boxes][easy-shulker-boxes]

6. Creates a default reference definition using the existing URL.

   The existing URL is always used as the fallback, regardless of whether it
   is a CurseForge or Modrinth URL.

   For example:

   [easy-shulker-boxes]: https://www.curseforge.com/minecraft/mc-mods/easy-shulker-boxes

7. Creates a platform specific reference definition for the platform from
   which the URL originated.

   For example:

   [easy-shulker-boxes-curseforge]: https://www.curseforge.com/minecraft/mc-mods/easy-shulker-boxes

8. If a platform specific URL is missing, attempts to derive the corresponding
   URL automatically.

   For example, a CurseForge mod URL:

   https://www.curseforge.com/minecraft/mc-mods/easy-shulker-boxes

   produces the following Modrinth candidate:

   https://modrinth.com/mod/easy-shulker-boxes

   Generated URLs are only suggestions. The script never assumes that a
   derived URL is correct without user confirmation.

9. Interactively asks the user to validate every missing platform specific URL.

   The user can choose one of three options:

   1. Accept the generated URL.
      The generated URL is added as the platform specific reference.

   2. Enter the correct URL.
      The user supplies the correct platform URL, which is added as the
      platform specific reference.

   3. There is no alternative link.
      No platform specific reference is created for that platform.

   When option 3 is selected, the default reference is still created. The
   custom link processor can therefore use the default URL when no
   platform specific reference exists.

10. Writes all generated reference definitions to the end of the Markdown
    file.

    A complete converted link may therefore look like:

    [Easy Shulker Boxes][easy-shulker-boxes]

    [easy-shulker-boxes]: https://www.curseforge.com/minecraft/mc-mods/easy-shulker-boxes
    [easy-shulker-boxes-curseforge]: https://www.curseforge.com/minecraft/mc-mods/easy-shulker-boxes
    [easy-shulker-boxes-modrinth]: https://modrinth.com/mod/easy-shulker-boxes

11. Prints detailed progress information while processing files, links,
    references, normalized legacy URLs, and interactively generated URLs.

12. Writes changes directly to the Markdown files.

The script does not perform any version control operations. It does not run
git pull, git add, git commit, git push, or any other Git command.

The directory is expected to have the following structure:

```

data/
├── cutthrough/
│   ├── about.md
│   ├── configuration.md
│   ├── features.md
│   └── ...
├── easy-shulker-boxes/
│   ├── about.md
│   ├── configuration.md
│   ├── features.md
│   └── ...
└── ...

```

Only about.md, configuration.md, and features.md are processed. Other Markdown
files and other files are ignored.

Mod directories are processed alphabetically.

Usage:

```

python3 convert_platform_links.py <data-directory>

```

Example:

```

python3 convert_platform_links.py 
/Users/user/Lokal/GitHub/modresources/pages/data

```

The script modifies the Markdown files in place. The supplied directory is
expected to be under version control so that the changes can be reviewed or
rolled back using the normal Git workflow, but this script itself performs no
version control operations.
"""

from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlparse
import re
import sys


CURSEFORGE_URL = "https://www.curseforge.com/"
LEGACY_CURSEFORGE_URL = "https://legacy.curseforge.com/"
MODRINTH_URL = "https://modrinth.com/"

MARKDOWN_FILE_NAMES = {
    "configuration.md",
    "about.md",
    "features.md",
}


def normalize_url(url):
    """Convert legacy CurseForge URLs to the current CurseForge URL."""

    if url.startswith(LEGACY_CURSEFORGE_URL):
        return CURSEFORGE_URL + url.removeprefix(LEGACY_CURSEFORGE_URL)

    return url


def get_platform(url):
    """Determine which supported platform a URL belongs to."""

    if url.startswith(CURSEFORGE_URL):
        return "curseforge"

    if url.startswith(MODRINTH_URL):
        return "modrinth"

    return None


def get_reference_name(url):
    """
    Derive a Markdown reference name from the final URL path component.

    Non-word characters are replaced with dashes and the result is converted
    to lowercase.

    Examples:

        easy-shulker-boxes → easy-shulker-boxes
        Some_Project      → some-project
        Fuzs              → fuzs
    """

    path = urlparse(url).path.rstrip("/")
    name = path.rsplit("/", 1)[-1]

    name = re.sub(r"[^\w]+", "-", name)
    name = name.replace("_", "-")
    name = name.strip("-").lower()

    return name


def derive_platform_url(url, target_platform):
    """
    Try to derive the equivalent URL for another platform.

    The resulting URL is only a guess and must be confirmed by the user.
    """

    parsed_url = urlparse(url)
    path_parts = [part for part in parsed_url.path.split("/") if part]

    if not path_parts:
        return None

    identifier = path_parts[-1]

    if target_platform == "curseforge":
        if path_parts[0] == "user":
            return f"{CURSEFORGE_URL}members/{identifier}"

        if path_parts[0] == "mod":
            return (
                f"{CURSEFORGE_URL}minecraft/mc-mods/{identifier}"
            )

    if target_platform == "modrinth":
        if path_parts[0] == "members":
            return f"{MODRINTH_URL}user/{identifier}"

        if "mc-mods" in path_parts:
            return f"{MODRINTH_URL}mod/{identifier}"

    return None


def ask_for_platform_url(reference_name, source_url, target_platform):
    """
    Ask the user how to handle a missing platform specific URL.

    Options:

        1. Accept the generated URL.
        2. Enter a different URL manually.
        3. Do not define an alternative URL.
    """

    derived_url = derive_platform_url(source_url, target_platform)

    print()
    print("=" * 80)
    print(f"Platform link required: {reference_name}")
    print(f"Existing URL:          {source_url}")
    print(f"Missing platform:      {target_platform}")

    if derived_url is not None:
        print(f"Generated URL:         {derived_url}")
    else:
        print("Generated URL:         Could not determine automatically")

    print()
    print("1. Accept the generated link")

    if derived_url is None:
        print("2. Enter the correct link")
    else:
        print("2. The generated link is incorrect, enter the correct link")

    print("3. There is no alternative link")

    while True:
        choice = input("\nChoose an option [1/2/3]: ").strip()

        if choice == "1":
            if derived_url is None:
                print("No generated URL is available.")
                continue

            print(f"Using: {derived_url}")
            return derived_url

        if choice == "2":
            while True:
                url = input("Enter the correct URL: ").strip()

                if not url:
                    print("Please enter a URL.")
                    continue

                if not url.startswith(("https://", "http://")):
                    print("Please enter a complete URL starting with https://.")
                    continue

                print(f"Using: {url}")
                return normalize_url(url)

        if choice == "3":
            print(
                f"No {target_platform} alternative will be defined. "
                "The default link will be used as the fallback."
            )
            return None

        print("Invalid option. Please enter 1, 2, or 3.")


def process_file(path):
    """Convert supported inline links in a Markdown file to reference links."""

    content = path.read_text(encoding="utf-8")

    references = OrderedDict()

    def replace_link(match):
        text = match.group("text")
        original_url = match.group("url")
        url = normalize_url(original_url)

        platform = get_platform(url)

        if platform is None:
            return match.group(0)

        reference_name = get_reference_name(url)

        print()
        print(f"Found {platform} link")
        print(f"  Text:      {text}")
        print(f"  URL:       {original_url}")
        print(f"  Reference: {reference_name}")

        if original_url != url:
            print(f"  Normalized: {url}")

        references.setdefault(reference_name, {})[platform] = url

        return f"[{text}][{reference_name}]"

    pattern = re.compile(
        r"(?<!!)\[(?P<text>[^\]]+)\]\((?P<url>https://[^)\s]+)\)"
    )

    content = pattern.sub(replace_link, content)

    if not references:
        print("No supported platform links found.")
        return False

    print()
    print("Creating link references")

    definitions = []

    for reference_name, urls in references.items():
        fallback_url = (
            urls.get("curseforge")
            or urls.get("modrinth")
        )

        print()
        print("-" * 80)
        print(f"Reference: {reference_name}")
        print(f"Fallback:  {fallback_url}")

        definitions.append(
            f"[{reference_name}]: {fallback_url}"
        )

        for platform in ("curseforge", "modrinth"):
            platform_url = urls.get(platform)

            if platform_url is None:
                platform_url = ask_for_platform_url(
                    reference_name,
                    fallback_url,
                    platform,
                )

            if platform_url is None:
                continue

            print(
                f"Adding {platform} reference: {platform_url}"
            )

            definitions.append(
                f"[{reference_name}-{platform}]: {platform_url}"
            )

    content = content.rstrip() + "\n\n" + "\n".join(definitions) + "\n"

    path.write_text(content, encoding="utf-8")

    print()
    print(f"Updated: {path}")

    return True


def main():
    """
    Convert CurseForge and Modrinth links to platform aware link references.

    Only the following files are processed:

        configuration.md
        about.md
        features.md

    Usage:

        convert_platform_links.py <directory>
    """

    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <directory>")
        sys.exit(1)

    root_directory = Path(sys.argv[1]).expanduser().resolve()

    if not root_directory.is_dir():
        print(f"Directory not found: {root_directory}")
        sys.exit(1)

    print("=" * 80)
    print("Platform Link Converter")
    print("=" * 80)
    print(f"Root directory: {root_directory}")
    print()

    processed_files = 0

    for project_directory in sorted(root_directory.iterdir()):
        if not project_directory.is_dir():
            continue

        print()
        print("=" * 80)
        print(f"Project: {project_directory.name}")
        print("=" * 80)

        for file_name in sorted(MARKDOWN_FILE_NAMES):
            path = project_directory / file_name

            if not path.is_file():
                continue

            print()
            print(f"Processing file: {file_name}")

            if process_file(path):
                processed_files += 1

    print()
    print("=" * 80)
    print("Conversion complete")
    print("=" * 80)
    print(f"Updated Markdown files: {processed_files}")


if __name__ == "__main__":
    main()
