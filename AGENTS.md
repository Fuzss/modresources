# AGENTS.md

Repository-wide instructions for agents working in `modresources`.

## Repository overview

This repository hosts web content, Maven artifacts, and tooling for **@heyitsfuzs** mods.

- `gradle/` – legacy Gradle build scripts, no longer used on modern versions.
- `maven/` – published mod API artifacts, indexed by CI.
- `pages/` – generated mod page content.
- `scripts/` – Python tooling for modding, porting, and deployment.
- `update/` – NeoForge / Forge update checker files.
- `.github/` – GitHub Actions and CI helper scripts.

## General rules

- Do not commit unless the user explicitly asks.
- Keep changes scoped to the area you are working in and match its existing conventions.
- Use the standard library and existing tooling; do not introduce new dependencies or build configuration unless asked.
- Never write absolute local paths or usernames into committed files; use a placeholder such as `~/...` or `fuzs.multiloader.project.mods`.

## Area-specific instructions

Subtrees provide their own `AGENTS.md`. The nearest file to the working
directory takes precedence, so work in a subtree follows that subtree's rules.

- `scripts/AGENTS.md` – Python modding tooling, entry-point contract, and style.
- `pages/AGENTS.md` – mod page writing style.
