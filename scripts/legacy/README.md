# `scripts/legacy/` — archival script index

> **This directory is archival. Do not execute, import, lint, refactor, or
> modify anything under `scripts/legacy/` (including the files listed below).**
> It is kept only as a historical record of one-off migrations and batch
> operations. Nothing here is imported or invoked by `scripts/main/`; the
> active tooling is documented in [`../main/README.md`](../main/README.md).

This index is the only documentation file in `scripts/legacy/`; it does not
affect any script. Paths are relative to this directory. Descriptions are
inferred by reading each script; no script here was executed.

Excluded from this index and **never to be read or touched**:

- `26.2.x/.venv/` — bundled virtual environment for the texture scripts.
- any `__pycache__/` directory.

Several scripts contain hardcoded absolute paths (`/Users/user/Lokal/GitHub`)
and the version-port scripts embed a hardcoded GitHub token placeholder in the
remote URL. Treat all of them as historical and unsafe to run as-is.

## Top level

| Script | What it did |
| --- | --- |
| `add_new_mod.py` | Interactive helper that prompts for a mod id and distribution slugs/IDs and writes a new `../mods/<mod-id>.json` with default dependencies (`fabricapi`, `forgeconfigapiport`, `puzzleslib` required), environments, and loaders (`fabric`, `neoforge`). |
| `configure_modrinth_disclosures.py` | macOS UI automation (`osascript` + Safari) that opened each mod's Modrinth *Settings → Disclosures* page and set the "LLMs may have assisted…" disclosure text, processing mod directories alphabetically with an optional starting project argument. |
| `convert_platform_links.py` | Converted inline CurseForge/Modrinth links in each mod's `about.md`, `configuration.md`, and `features.md` (under a `pages/data` tree) into platform-aware Markdown reference links, normalizing legacy CurseForge URLs and interactively deriving the missing platform URL. |
| `determinte_project_size.py` | Walked a hardcoded root and ranked each mod directory by the total size of its `1.21.8/**/*.java` files, printing human-readable sizes. (The filename typo is original.) |
| `sort_access_widener.py` | Rewrote a class-tweaker / access-widener file in place, grouping transitive entries first and sorting by class name, object type (`class`, `field`, `method`), member name, descriptor, and access level. |

## `1.21.1/`

| Script | What it did |
| --- | --- |
| `update_gradle_properties.py` | Batch migration of `<root>/<project>/1.21.1/gradle.properties`: renamed the Fabric Forge Config API Port artifact, pinned `dependenciesVersionCatalog=1.21.1-SNAPSHOT`, commented out the PuzzlesLib version properties, removed all `dependenciesOptional*` properties and the `# Optional Dependencies` heading, and replaced the legacy Gradle config block. |

## `1.21.7/`

| Script | What it did |
| --- | --- |
| `1.21.5_1.21.7.py` | One-off port helper for a single project: copied the workspace template `.gitignore` and `CHANGELOG.md`, copied the `1.21.5` branch tree to `1.21.7`, removed `.idea`, updated `gradle.properties` (`modVersion=21.7.0`, catalog `1.21.7-v1`, PuzzlesLib `21.7.1`), patched `NeoForge/build.gradle`, and ran `commonGenSources`, `neoforgeData`, and `fabricClient`. Upload/commit steps were left commented out. |
| `1.21.6_1.21.7.py` | Same one-off port helper for `1.21.6` → `1.21.7`, but moving the source branch instead of copying it and finishing with `allUploadEverywhere` and a `full 1.21.7 port` commit/push. |

## `1.21.8/`

| Script | What it did |
| --- | --- |
| `1.21.7_1.21.8.py` | One-off port helper for `1.21.7` → `1.21.8`: refreshed `.gitignore` and `.github`, moved the branch, removed `.idea` and `.gradle`, updated `gradle.properties`, removed the legacy NeoForge launch patch and the `# Optional Dependencies` block (aborting if absent), ran `commonGenSources` and `neoforgeData`, uploaded everywhere unless `skipUpload=true` was passed, then committed and pushed the `full 1.21.8 port`. |

## `26.1.x/`

| Script | What it did |
| --- | --- |
| `git_split_main.py` | Destructive history rewrite: cloned a repo whose version directories matched `\d+\.\d+\.(\d+|x)`, created one branch per version with `git filter-repo --subdirectory-filter`, force-pushed each branch, then rewrote `main` with `git filter-repo --invert-paths` to remove the version directories and force-pushed it. |

## `26.2.x/`

These texture scripts require Pillow (the bundled `26.2.x/.venv/` was used to
run them) and are not part of the stdlib-only `scripts/main/` tooling.

| Script | What it did |
| --- | --- |
| `create_sign_texture.py` | Remapped a 32×32 sign texture into the new 24×26 texture layout. |
| `convert_sign_texture.py` | Converted the old 64×32 sign texture into the new 32×32 layout, remapping all six faces and edges (flipping the bottom face). |
| `convert_hanging_sign_texture.py` | Converted the old 64×32 hanging-sign texture into the new 32×32 layout, remapping the sign body and repositioning the chains. |

## `main/`

| Script | What it did |
| --- | --- |
| `update_version_properties.py` | Copied the five `distributions.*` properties from each mod's primary-branch `gradle.properties` into the flat `properties` object of that mod's `main/versions.json`, then committed and pushed each changed file (`Update version properties`). Run before `transform_versions_distributions.py`. |
| `transform_versions_distributions.py` | Converted the flat `properties` distribution keys in each mod's `main/versions.json` into a nested `distributions` object, then committed and pushed each changed file (`Transform version distributions`). |
| `validate_distribution_properties.py` | Read-only validation of `distributions.curseforge` and `distributions.modrinth` between each mod's `versions.json` and the matching `<mod-id>.json` in Mod Resources (mod id = folder name without dashes), printing each mismatching property. Performed no file writes and no Git operations. |

These scripts handled distribution metadata that the active tooling now reads
from `gradle.properties` instead of `versions.json`. Within this old workflow,
`update_version_properties.py` produced the flat `properties` format that
`transform_versions_distributions.py` then nested, so their order mattered.
