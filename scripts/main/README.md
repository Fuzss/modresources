# `main.py` — mod project management CLI

`scripts/main/main.py` is the single control entry point for the modding
workflow in this repository. It clones and prepares version branches, runs
workspace upgrades, edits Gradle properties and the changelog, and drives the
Gradle tasks that refresh, generate data, launch, build, publish, upload, and
notify.

All heavier logic lives in the `core/` modules next to it (see
[Module map](#module-map--architecture)). This README is the canonical CLI
reference for the tooling.

## The single-entry contract

- `main.py` owns argument parsing, validation, and dispatch. It stays at
  `scripts/main/main.py`; do not add a second CLI entry point for the same
  workflow.
- Before importing the workflow modules, `main.py` inserts `<scripts/main>/core`
  at the front of `sys.path`, so the `core/` modules are imported by bare name
  (`import clone_versions`, `from cli import parse_args`, ...). The `config/`
  path is resolved relative to the working directory, so run it from
  `scripts/main/`:

  ```sh
  cd scripts/main
  ./main.py --minecraft 26.2.x --name example-mod
  ```

  `--help` works from any directory because argparse exits before any relative
  path is used.
- Each `tools/*.py` script performs the same bootstrap for the core module it
  needs: it inserts `<scripts/main>/../core` on `sys.path` before importing
  `gradle_user_properties`.
- All modules are stdlib-only. They never import third-party packages.

## Requirements

- Python 3.12 or newer.
- A working `git` installation with access to `git@github.com:Fuzss/<name>.git`.
- A project checkout containing the Gradle wrapper (`./gradlew`).
- macOS for `tools/update_curseforge_bodies.py` (it uses `pbcopy`, `osascript`,
  and Safari); the core CLI and the Modrinth updater are portable (the latter
  needs `curl` and network access).
- User Gradle properties (next section).

## User Gradle properties

The tooling reads `~/.gradle/gradle.properties`, parsed by
`core/gradle_user_properties.load_gradle_properties`. The properties actually
read are:

| Property | Required by | Meaning |
| --- | --- | --- |
| `fuzs.multiloader.project.mods` | `main.py`, both `tools/` body scripts | Directory containing the individual mod repositories (the project root). |
| `fuzs.multiloader.project.resources` | `tools/update_curseforge_bodies.py`, `tools/update_modrinth_bodies.py` | Resources repository containing the generated `pages/out/` project pages. |
| `fuzs.multiloader.project.modrinth.token` | `tools/update_modrinth_bodies.py` | Bearer token used to authenticate the Modrinth API request. |

`main.py` calls `find_gradle_property("fuzs.multiloader.project.mods")` and
aborts with a logged error when the file or the property is missing. The
effective project root is `<fuzs.multiloader.project.mods>/<name>` unless
`--path` overrides it.

Example:

```properties
# ~/.gradle/gradle.properties
fuzs.multiloader.project.mods=/Users/me/Projects/mods
fuzs.multiloader.project.resources=/Users/me/Projects/modresources
fuzs.multiloader.project.modrinth.token=xxxxxxxxxxxxxxxx
```

## Execution order

`main.py` runs its steps in a fixed order. Knowing it matters, because later
steps depend on earlier ones and some steps require `--version`.

1. Parse and print the resolved arguments as JSON, then derive `--id` from
   `--name` when omitted.
2. Resolve `base_path`, `root_path`, `main_path`, and `project_path`.
3. `--init`: clone the repository and (with `--version` and a source branch)
   create the version branch.
4. `git pull` in `main/` and the version directory, unless `--open` or `--bare`.
5. `--open`: launch Finder or IntelliJ and exit with code 0.
6. `--branch`: update support statuses in `versions.json`.
7. `--upgrade`: run the workspace upgrade.
8. Rewrite `gradle.properties`; resolve `--version` from the file afterwards.
9. `--version`: update `CHANGELOG.md` from `--changelog`.
10. `--gradle`: update `gradle/wrapper/gradle-wrapper.properties`.
11. `--spotless`: run the update-specific formatting tasks.
12. Project refresh: `./gradlew`, plus `:Fabric:fabric-validate` when a Fabric
    subproject exists.
13. `--data`: run data generation.
14. `--launch`: run the launch tasks.
15. `--commit`: commit and push the resolved version.
16. `--publish`: publish to Maven.
17. `--upload`: upload to the distribution sites.
18. `--notify`: send the Discord notification.

`--bare` skips the git pull (step 4) and the `./gradlew`-based steps: spotless
(11), refresh (12), data (13), launch (14), publish (16), upload (17), and
notify (18). It still writes `gradle.properties`, still commits with
`--commit` (15), and still rewrites the wrapper properties file in step 10 —
it only skips the `./gradlew wrapper` invocation. Steps that need a version
(`--commit`, `--publish`, `--upload`, `--notify`, and changelog handling)
print a warning and skip when `--version` is absent.

## Flag reference

Derived from `./main.py --help`. Unless noted, a flag's config key in a
`--config` file is its long name without the leading `--`.

| Flag | Metavar / arguments | Default | Description |
| --- | --- | --- | --- |
| `-h`, `--help` | | | Show help and exit. |
| `--bare` | | off | Skip any Gradle setup. Also suppresses the `git pull` performed in step 4 and all `./gradlew` invocations. |
| `--branch` | `BRANCH_NAME SUPPORT_STATUS` | `[]` | Update branch status in `versions.json`; repeatable. Format: `--branch <branch_name> <support_status>`. Statuses: `primary`, `maintained`, `fixes`, `archived` (an unknown status warns; an empty status removes the branch). |
| `--catalog` | `VERSION_CATALOG` | none | Version-based catalog. Example: `--catalog 26.2-SNAPSHOT`. Writes `project.libs` (legacy `dependenciesVersionCatalog`). |
| `--changelog` | `SECTION_NAME TEXT` | none | Add a changelog line; repeatable. Format: `--changelog <section_name> <text>`. Sections: `added`, `changed`, `deprecated`, `removed`, `fixed`, `security`. Requires `--version`. |
| `--commit` | | off | Commit to GitHub. Requires `--version`; not skipped by `--bare`. |
| `--config` | `CONFIG_NAME` | none | Args as JSON config file. Example: `--config upgrade-upload`. Loads `config/<--minecraft>/<name>.json`. |
| `--data` | | off | Generate data (`neoforge-data`; legacy `neoForgeData`). Skipped by `--bare`. |
| `--gradle` | `GRADLE_VERSION` | none | Gradle wrapper version. Example: `--gradle 9.6.0`. Rewrites `distributionUrl` and, unless `--bare`, runs `./gradlew wrapper --gradle-version <version>`. |
| `--id` | `MOD_ID` | derived | Mod id. Example: `--id examplemod`. Defaults to `--name` with hyphens removed. |
| `--init` | `[SOURCE_BRANCH]` | none | Setup git repository and version branch, with optional argument. Example: `--init [26.2.x]`. Without a value, clones only the `--minecraft` branch. With a source branch (and `--version`), clones the versions listed in `versions.json` and then creates `<--minecraft>` from that source branch; a source branch without `--version` is an error. |
| `--launch` | `[MOD_LOADER [DISTRIBUTION ...]]` | `[]` | Launch the game; repeatable. Format: `--launch <mod_loader> <distribution>`. Loaders: `fabric`, `neoforge`. Distributions: `client`, `server`. Omit both to auto-detect client (Fabric first, then NeoForge); give only a loader to default to `client`. |
| `--legacy` | `[SCOPE]` | none | Use legacy Gradle property and task names. Scopes: `properties`, `tasks`. Without a value, both scopes apply. |
| `--minecraft` | `MINECRAFT_VERSION` | **required** | Minecraft name. Example: `--minecraft 26.2.x`. |
| `--name` | `REPOSITORY_NAME` | **required** | Repository name. Example: `--name example-mod`. |
| `--notify` | | off | Notify via Discord webhook (`all-discord`; legacy `notifyDiscord`). Requires `--version`; skipped by `--bare`. |
| `--open` | `[ENVIRONMENT ...]` | none | Open in Finder, or Idea. Format: `--open <environment>`. Environments: `finder`, `idea`. Without a value, defaults to `finder`. Resolved after any `--init` work and before every other step; it skips the git pull and exits with code 0. |
| `--path` | `ROOT_PATH` | derived | Override default root path. Example: `--path /absolute/path/to/project`. Default is `<fuzs.multiloader.project.mods>/<name>`. |
| `--plugins` | `PLUGINS_VERSION` | none | Multiloader convention plugins version. Example: `--plugins 1.1-SNAPSHOT`. Writes `project.plugins`. |
| `--properties` | `KEY VALUE` | none | Set a `gradle.properties` value; repeatable. Format: `--properties <key> <value>`. |
| `--publish` | | off | Publish to Maven (`all-publish`; legacy `allPublish`). Requires `--version`; skipped by `--bare`. |
| `--spotless` | `TASK_NAME` | none | Run spotless upgrade tasks for a specific game update. Example: `--spotless tinytakeover`. Mapped names: `tinytakeover`, `mountsofmayhem`, `thecopperage`; other values run only `all-java-apply`. Skipped by `--bare`. |
| `--upgrade` | `[PATCHES_NAME]` | none | Run workspace upgrade, potentially for a specific version, with optional argument. Targets: `26.1.x`, `1.21.11`, `1.21.1`, and the generic `26.2.x`; unknown targets error. Without a value, only the generic refresh runs. Requires clean worktrees. |
| `--upload` | `[MOD_LOADER [WEBSITE ...]]` | none | Upload to CurseForge, Modrinth, or GitHub. Format: `--upload <mod_loader> <website>`. Loaders: `fabric`, `neoforge`. Sites: `curseforge`, `modrinth`, `github`. Without values, upload everywhere; a single loader or site fills the other slot. Requires `--version`; skipped by `--bare`. |
| `--version` | `PROJECT_VERSION` | none | Mod version. Example: `--version 26.2.0`. Also accepts `latest`, `patch`, `minor`, `major`; the bump keywords are resolved against `mod.version` (legacy `modVersion`). |

Notes:

- `parse_args` prints the fully resolved arguments as sorted JSON before any
  work starts. This is the easiest way to see what a `--config` file merged.
- `--config` values only fill arguments that are still at their argparse
  default, so an explicit CLI flag always wins over the config file.
- Unknown config keys are fatal; the process exits with a logged error.

## `--config` JSON schema

`--config <name>` loads `config/<--minecraft>/<name>.json` relative to
`scripts/main/`. The file is a single JSON object whose keys are the long option
names without `--` (`argparse` destination names) and whose values match the
option shape:

- booleans (`store_true`): `bare`, `commit`, `data`, `notify`, `publish`.
- strings: `catalog`, `gradle`, `id`, `path`, `plugins`, `spotless`, `version`.
  (`minecraft` and `name` are required on the command line and cannot usefully
  be supplied by config.)
- optional-one-of: `init` (string or `true`), `legacy` (string or `true`),
  `upgrade` (string or `true`).
- repeatable pairs (`append`, `nargs=2`): `branch` (`[[name, status], ...]`),
  `changelog` (`[[section, text], ...]`), `properties` (`[[key, value], ...]`).
- variadic lists: `launch` (`[[]]` means "auto-detect"; `[["fabric", "client"]]`
  for one explicit target), `upload` (`[]` means "all loaders, all sites").
- `open` is a variadic list; `[]` defaults to `finder`.

Unknown keys are rejected with `Unknown config key: <key>`.

### Bundled examples

All bundled files use the same shape. `config/26.2.x/update.json` is the
smallest:

```json
{
  "data": true,
  "commit": true,
  "launch": [[]],
  "upload": []
}
```

With `--config update`, that selects `--data --commit`, an auto-detected client
launch, and an upload to every site.

| File | Keys set |
| --- | --- |
| `config/1.21.1/update.json` | `data`, `commit`, `launch`, `upload` |
| `config/26.1.x/update.json` | `data`, `commit`, `launch`, `upload` |
| `config/26.2.x/update.json` | `data`, `commit`, `launch`, `upload` |
| `config/1.21.1/downgrade.json` | `version`, `init`, `catalog`, `plugins`, `changelog`, `branch`, `gradle`, `upgrade`, `spotless`, `commit`, `data`, `launch`, `upload` |
| `config/26.1.x/upgrade.json` | `version`, `init`, `catalog`, `plugins`, `changelog`, `branch`, `gradle`, `upgrade`, `spotless`, `commit`, `data`, `launch`, `upload` |
| `config/26.2.x/upgrade.json` | `version`, `init`, `catalog`, `plugins`, `changelog`, `branch`, `gradle`, `upgrade`, `commit`, `data`, `launch`, `upload` |

The port configs (`config/26.1.x/upgrade.json`, `config/26.2.x/upgrade.json`,
and `config/1.21.1/downgrade.json`) cover a full version port: they set the
target `version`, the source `init` branch, the `catalog` and `plugins`
versions, the changelog entry, the `branch` status updates, the Gradle wrapper
version, and the `upgrade` target. `config/1.21.1/downgrade.json` additionally
sets `spotless`. None of the bundled files set `name` or `minecraft`, so those
required options must still be passed on the command line (use `--path` to
override the project root when needed).

## Module map / architecture

`scripts/main/` is a stdlib-only, package-free layout. `main.py` stays at the
root; the workflow modules live in `core/` and the standalone batch scripts in
`tools/`.

`main.py` inserts `core/` on `sys.path` before importing its modules, so the
`core/` modules import each other by bare name. Each `tools/*.py` script
inserts `<scripts/main>/../core` on `sys.path` before importing
`gradle_user_properties`. The working directory still matters for the relative
`config/` path and for the project-relative `git` and `./gradlew` operations
when running `main.py`.

| Module | Role |
| --- | --- |
| `main.py` | CLI entry point. Parses, validates, and dispatches the workflow in a fixed order; adds `core/` to `sys.path`. |
| `core/cli.py` | Argparse definitions and `--config` JSON merging. Source of truth for the CLI surface. |
| `core/console.py` | Timestamped, colored `info2` / `warn2` / `error2` logging. `error2` exits with code 1. |
| `core/validation.py` | Validates and normalizes parameter sets (`--open`, `--launch`, `--upload`, `--legacy`). |
| `core/fs_utils.py` | Filesystem and text helpers: subproject probe, template copy, move/remove, regex replace, license-year bump. |
| `core/git_ops.py` | Git commit/push and new-version-branch preparation. |
| `core/clone_versions.py` | Reads/creates `versions.json`, clones `main` and version branches. |
| `core/gradle_user_properties.py` | Parses `~/.gradle/gradle.properties`. |
| `core/gradle_properties.py` | Reads/edits project `gradle.properties` and resolves version bumps. |
| `core/gradle_tasks.py` | Maps `(loader, distribution)` and `(loader, site)` to Gradle task names. |
| `core/changelog.py` | Parses `--changelog` pairs and prepends a Keep-a-Changelog entry. |
| `core/workspace_upgrade.py` | Orchestrates version upgrades and the legacy-file cleanup. |
| `core/migrate_mixins.py` | Converts `mixins.json` into Gradle DSL mixin declarations. |
| `core/migrate_mod_properties.py` | Migrates the legacy `gradle.properties` layout to current names. |
| `tools/update_curseforge_bodies.py` | Standalone macOS script that batch-updates CurseForge descriptions. |
| `tools/update_modrinth_bodies.py` | Standalone script that batch-updates Modrinth descriptions through the API. |

Dependency sketch:

```
main.py ──(inserts core/ on sys.path)──> core/
core/
├── cli.py ─────────────── console.py
├── clone_versions.py
├── git_ops.py ─────────── fs_utils.py ── console.py
├── gradle_properties.py ─ gradle_user_properties.py ── console.py
├── gradle_tasks.py ────── console.py
├── changelog.py ───────── validation.py ── fs_utils.py
├── validation.py
└── workspace_upgrade.py
    ├── migrate_mixins.py
    ├── migrate_mod_properties.py ── console.py
    ├── fs_utils.py
    └── git_ops.py

tools/  (each inserts ../core on sys.path)
├── update_curseforge_bodies.py ──> core/gradle_user_properties.py
└── update_modrinth_bodies.py ────> core/gradle_user_properties.py
```

The `core/migrate_*.py` modules are also runnable standalone, and the
`tools/update_*_bodies.py` scripts are standalone-only. None are dispatched by
`main.py` (except `core/migrate_mixins.py` and `core/migrate_mod_properties.py`,
which `core/workspace_upgrade.py` calls). See
[Standalone tools](#standalone-tools).

### `versions.json`

`core/clone_versions.py` reads and writes `main/versions.json`, which maps version
branches to a support status:

```json
{
  "branches": {
    "26.2.x": "primary",
    "26.1.x": "maintained",
    "1.20.1": "fixes"
  }
}
```

Support statuses: `primary`, `maintained`, `fixes`, `archived`. Branches with
status `archived` are not cloned by `load_versions`. `--branch` both updates
the status and removes a branch when given an empty status.

## Common workflows

All examples run from `scripts/main/`. Replace the names with your projects.

### Port / upgrade a project to a new version

A full port is driven by a bundled `upgrade` config. For `26.2.x` it sets the
version, source branch, catalog, plugins, changelog, branch statuses, Gradle
wrapper, and upgrade target:

```sh
./main.py --minecraft 26.2.x --config upgrade --name example-mod
```

To do the same explicitly (config contents inlined):

```sh
./main.py --minecraft 26.2.x --name example-mod \
  --version 26.2.0 --init 26.1.x --upgrade 26.2.x \
  --catalog 26.2-SNAPSHOT --plugins 1.1-SNAPSHOT \
  --changelog changed "Update to Minecraft 26.2.x" \
  --branch 26.2.x primary --branch 26.1.x maintained \
  --gradle 9.6.1 --data --launch --commit --upload
```

For an existing checkout that only needs the generic refresh without creating a
branch, use `--upgrade` with no value (or the target) and no `--init`.

### Release a patch

Add a changelog entry, bump the version, generate data, launch (smoke test),
commit, and upload:

```sh
./main.py --minecraft 26.2.x --name example-mod \
  --version patch --changelog fixed "Fix broken special item models" \
  --data --launch --commit --upload
```

Or reuse the update config and pass only the parts that vary:

```sh
./main.py --minecraft 26.2.x --config update --name example-mod \
  --version patch --changelog changed "Improve leaf particle tint"
```

`--commit --upload` without `--changelog` is valid when the changelog entry
already exists; omitting `--changelog` without a matching entry aborts with a
missing-version error.

### Publish to Maven

```sh
./main.py --minecraft 26.2.x --name example-mod \
  --version 26.2.0 --commit --data --publish
```

`--publish` runs `all-publish` (legacy `allPublish`) and, like the other
release steps, requires `--version`.

### Upload only

Upload one loader to one site, or one loader to every site:

```sh
./main.py --minecraft 26.2.x --name example-mod --version 26.2.1 --upload fabric curseforge
./main.py --minecraft 26.2.x --name example-mod --version 26.2.1 --upload neoforge
./main.py --minecraft 26.2.x --name example-mod --version 26.2.1 --upload
```

The last form uploads every loader to every site. Add `--notify` to announce
afterwards.

### Open a project in an editor

```sh
./main.py --minecraft 26.1.x --name example-mod --open idea
./main.py --minecraft 26.2.x --name example-mod --open          # Finder
```

`--open` skips the git pull, launches the environment, and exits with code 0.

### Set a bundled library version

```sh
./main.py --minecraft 26.2.x --name example-mod \
  --properties project.libs.versions.iteminteractions 26.2.2 \
  --version patch --changelog changed "Bump bundled Item Interactions library" \
  --commit --upload
```

### Legacy branches

On older branches, select the legacy property and task names:

```sh
./main.py --minecraft 1.20.4 --name example-mod \
  --version latest --data --upload --legacy
```

Use `--legacy properties` or `--legacy tasks` for only one scope.

### Refresh an existing checkout

```sh
./main.py --minecraft 26.2.x --name example-mod
```

This resolves and prints the arguments as JSON, pulls the repositories, updates
`gradle.properties`, and runs the `./gradlew` project refresh. Add `--bare` to
skip the pulls and every `./gradlew` step.

## Standalone tools

These scripts can be run directly (from `scripts/main/`) and are not dispatched
by `main.py`:

```sh
python3 core/clone_versions.py <repo-name>
python3 core/migrate_mixins.py <mixins.json> <build.gradle>
python3 core/migrate_mod_properties.py <input> <output> <plugins_version>
python3 tools/update_curseforge_bodies.py [project]
python3 tools/update_modrinth_bodies.py [project]
```

`tools/update_curseforge_bodies.py` is macOS-only (it drives Safari through
`osascript` and uses `pbcopy`); `tools/update_modrinth_bodies.py` only needs
`curl` and network access. Both require the user properties listed above,
process projects alphabetically, and accept an optional project name to resume
from; neither performs git operations. For a detailed description of their
behavior, see their module docstrings.

## Verification

There is no test suite. From the repository root, run:

```sh
python3 -m py_compile scripts/main/main.py scripts/main/core/*.py scripts/main/tools/*.py
python3 scripts/main/main.py --help
```

`py_compile` must pass with no output, and `--help` must print the usage and
option list and exit with code 0. Run `./main.py --help` from `scripts/main/`
as well when changing the CLI, because that is the directory the real workflow
runs from.

When changing only documentation, `git diff` should contain only docstrings,
comments, and `*.md` files; no `.py` logic should change.

## See also

- `../../AGENTS.md` and `../AGENTS.md` — repository and subtree agent
  instructions.
