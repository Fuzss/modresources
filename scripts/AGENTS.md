# AGENTS.md

Instructions for agents working in the `scripts/` subtree (Python modding
tooling). This file is scoped to `scripts/`; repository-wide guidance lives in
the root `AGENTS.md`.

## Python tooling

All active Python tooling lives in `scripts/main/`:

| File | Purpose |
| --- | --- |
| `main.py` | Core CLI entry point for project management tasks. |
| `clone_versions.py` | Clones and prepares version-based git repositories. |
| `migrate_mixins.py` | Converts `mixins.json` files into Gradle DSL. |
| `migrate_mod_properties.py` | Migrates legacy `gradle.properties` layout. |
| `update_curseforge_bodies.py` | Batch-updates CurseForge project bodies. |
| `update_modrinth_bodies.py` | Batch-updates Modrinth project bodies. |

Sibling modules extracted from `main.py` (`console.py`, `fs_utils.py`,
`gradle_properties.py`, `gradle_user_properties.py`, `validation.py`,
`changelog.py`, `git_ops.py`, `gradle_tasks.py`, `workspace_upgrade.py`,
`cli.py`) are imported by bare name and must stay in `scripts/main/`.

`scripts/legacy/` is archival only. Do not modify, lint, or refactor anything there. In particular, never touch the bundled `.venv` under `scripts/legacy/26.2.x/` or any `__pycache__` directory. Reading legacy scripts is permitted only for the `python-documenter` subagent, which may produce a read-only `scripts/legacy/README.md` index; it must never edit legacy `.py` files.

### Hard rules

1. `scripts/main/main.py` is the single control entry point for modding tasks. It must stay fully intact as the entry point; keep the CLI surface and dispatch behavior stable.
2. Do not change functionality unless explicitly asked. Signal any required functional change to the user instead of silently applying it.
3. Preserve externally observable behavior: CLI flags, output text, generated file contents, git commands, and Gradle task names must remain identical during cleanup or refactoring.
4. Keep the scripts dependency-free. Use the standard library only. Do not add third-party packages, `pyproject.toml`, or new tooling unless the user asks.
5. `main.py` uses bare sibling imports and relative paths, so it must be run from `scripts/main/` (e.g. `./main.py --minecraft 26.2.x --name example-mod`). Do not introduce a package layout that breaks this.
6. Do not commit unless the user explicitly asks.

### Style conventions

- Python 3.12+ baseline. 4-space indentation, `snake_case` functions and variables, `PascalCase` only for classes (none currently).
- Prefer explicit `os.path` / `pathlib` handling already present in each file; match the surrounding file rather than rewriting its idioms.
- Keep `main.py` focused on orchestration: parsing, validation, and dispatch. Extract cohesive, reusable logic into sibling modules when refactoring, but leave a thin, readable CLI in `main.py`.
- Fatal errors in `main.py` go through `error2(...)`; avoid raising raw exceptions that skip the logging path unless the existing code already does so.
- Use module and function docstrings for non-trivial logic. Do not add narration comments to obvious code.

### Documentation

- The `python-documenter` subagent owns documentation consistency. Its prompt (`scripts/.opencode/agent/python-documenter.md`) is the source of truth for the docstring and README standard.
- Module docstrings state purpose, entry points, side effects (filesystem / git / subprocess / network), and constraints. Non-trivial functions document `Args` / `Returns` / `Raises` and side effects.
- Write for two audiences: humans (readable prose and examples) and agents (stable headings, explicit contracts and invariants).
- Documentation-only changes must not alter behavior. Verify with `py_compile` and `./main.py --help`.
- Canonical CLI reference is `scripts/main/README.md`.

### Verification

There is no test suite. After any change, verify with:

```sh
python3 -m py_compile scripts/main/*.py
cd scripts/main && ./main.py --help
```

Run `./main.py --help` from `scripts/main/` so imports and relative config paths resolve.
