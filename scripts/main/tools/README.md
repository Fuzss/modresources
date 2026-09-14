# `tools/` — standalone description updaters

Two standalone scripts that publish every mod's generated page as its project
description on Modrinth and CurseForge. Neither is dispatched by `main.py`;
run them directly. For the core CLI, see [`../README.md`](../README.md).

| Script | Site | Mechanism |
| --- | --- | --- |
| [`update_modrinth_bodies.py`](update_modrinth_bodies.py) | Modrinth | Modrinth API via `curl` (`PATCH`). |
| [`update_curseforge_bodies.py`](update_curseforge_bodies.py) | CurseForge | macOS Safari UI automation via `osascript`. |

## Common behavior

- Enumerate every directory under the configured mods directory,
  alphabetically.
- For each project, read its `main/versions.json` and the generated page under
  `pages/out/<project>/`; skip projects missing the site id/slug, the body
  file, or `versions.json`.
- An optional project name resumes from that project (inclusive) onward; if the
  name is not found, print `Project not found: <name>` and exit with code 1.
- Neither script performs any git operation. Both print progress per project.

## Requirements

| Requirement | Modrinth tool | CurseForge tool |
| --- | --- | --- |
| Python 3.12+ | yes | yes |
| `curl` + network | yes | no |
| macOS + Safari + Accessibility permission | no | yes |

The CurseForge tool drives Safari through System Events, so the terminal
running the script needs Accessibility/Automation permission, and Safari must be
logged in to CurseForge.

## User Gradle properties

Both tools read `~/.gradle/gradle.properties` (via `core/gradle_user_properties`):

| Property | Used by | Meaning |
| --- | --- | --- |
| `fuzs.multiloader.project.mods` | both | Directory containing the individual mod repositories. |
| `fuzs.multiloader.project.resources` | both | Resources repository containing the generated `pages/out/` pages. |
| `fuzs.multiloader.project.modrinth.token` | Modrinth | Bearer token for the Modrinth API. |

## Inputs per project

| Tool | `versions.json` key | Body file |
| --- | --- | --- |
| Modrinth | `distributions.modrinth.id` | `<resources>/pages/out/<project>/modrinth.html` |
| CurseForge | `distributions.curseforge.slug` | `<resources>/pages/out/<project>/curseforge.html` |

`<project>` is the mod repository directory name exactly as it appears on disk
(hyphens included, e.g. `easy-shulker-boxes`).

## Usage

Run from `scripts/main/`:

```sh
python3 tools/update_modrinth_bodies.py                # all projects
python3 tools/update_modrinth_bodies.py example-mod    # resume at example-mod
python3 tools/update_curseforge_bodies.py              # all projects
python3 tools/update_curseforge_bodies.py example-mod  # resume at example-mod
```

The scripts add `../core` to `sys.path` themselves and read all paths from the
Gradle properties, so they can also be invoked from the repository root
(`python3 scripts/main/tools/update_modrinth_bodies.py`).

There is no "single project" mode: the optional argument resumes the batch at
that project and continues to the end.

## Modrinth tool

For each project with a `distributions.modrinth.id` and a generated
`modrinth.html`, it sends:

```text
PATCH https://api.modrinth.com/v2/project/<id>
Authorization: Bearer <fuzs.multiloader.project.modrinth.token>
Content-Type: application/json

{"body": "<generated HTML>"}
```

- The `Authorization` header is passed to `curl` through a config file on
  standard input, so the token never appears in the process argument list.
- `--fail-with-body` is used, so a failed request is reported
  (`Failed to update <project>: <stderr>`) and skipped without aborting the
  batch.
- A short delay is inserted between requests, and successful updates print
  `Updated <project>`.

## CurseForge tool

For each project with a `distributions.curseforge.slug` and a generated
`curseforge.html`, it:

1. Builds the legacy editor URL
   `https://legacy.curseforge.com/minecraft/mc-mods/<slug>/settings/description`
   and prints `Opening <url>`.
2. Copies the HTML to the macOS clipboard with `pbcopy`.
3. Activates Safari and navigates to the URL.
4. Uses System Events to switch to the HTML source editor, replace the contents
   with the clipboard (Command+A / Command+V), confirm, and save changes.

The click positions are fixed constants near the top of the script
(`SOURCE_MODE_BUTTON_COORDINATES`, `OK_BUTTON_COORDINATES`,
`SAVE_CHANGES_BUTTON_COORDINATES`). They depend on the Safari window size and
the CurseForge page layout and may need updating if either changes.

## Skip and failure messages

| Message | Meaning |
| --- | --- |
| `Skipping <project>: no Modrinth body file found` | No `pages/out/<project>/modrinth.html`. |
| `Skipping <project>: no CurseForge body file found` | No `pages/out/<project>/curseforge.html`. |
| `Failed to update <project>: ...` | Modrinth request failed; the batch continues. |
| `Project not found: <name>` | The resume project does not exist; exits 1. |
| `Updated <project>` | The description was submitted. |

## Verification

There is no test suite. Check the scripts still parse with:

```sh
python3 -m py_compile scripts/main/tools/*.py
```

Both tools have real side effects (API writes and UI automation) and no dry-run,
so test with a controlled resume point rather than a full batch.
