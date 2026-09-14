---
name: mod-page-authoring
description: Use when authoring or normalizing the About and Features text for Fuzss Minecraft mod pages, i.e. the files under pages/data/<local id>/about.md and features.md. Covers collecting a source brief and dispatching the page-author and page-style-auditor subagents.
---

# Mod page authoring

This skill drives the text pipeline for the `pages/` subtree. It produces
exactly two files per mod: `pages/data/<local id>/about.md` and
`features.md`. Images, `installation.yaml`, `sections.yaml`, `credits.md`,
`configuration.md`, and anything under `commons/` are manual and out of scope.

The writing standard is `pages/AGENTS.md`; read it before starting.
`<local id>` is the mod repository name with dashes removed (`air-hop` ->
`airhop`).

## Single mod

1. Pick the repository name (e.g. `eternal-nether`) and the branch
   (default `26.2.x`).
2. Build the authoring brief from the repository root:

   ```sh
   python3 scripts/main/tools/collect_page_brief.py <mod> --branch 26.2.x \
       --out pages/.authoring/briefs/<local id>.md
   ```

   Run this from the repository root. From `pages/`, prefix the script path with
   `../`. The collector reads the mods directory from
   `fuzs.multiloader.project.mods`; override with `--mods-root` when needed.
3. Dispatch the `page-author` subagent, giving it the brief path and the local
   id. It writes both markdown files in place and a guidance report at
   `pages/.authoring/guidance/<local id>.md`.
4. Dispatch the `page-style-auditor` subagent with the two file paths. If it
   reports `FAIL`, send the violations back to `page-author` and re-run the
   auditor.
5. Report: files written, feature count, guidance path, audit verdict, and any
   review notes.

## Batch (only when explicitly requested)

Normalization across many mods is a separate, deliberate pass:

1. Read the mod ids from `pages/input`, one per line, ignoring blanks and `#`.
2. Process them in small batches (about ten mods). For each batch, run steps 1-5
   above, one mod at a time, using a fresh `page-author` invocation per mod so
   context stays small.
3. Collect the guidance reports and summarize what manual assets are missing
   across the batch before reporting back.

Do not start a batch unless the user explicitly asks for it.

## Guardrails

- Never touch files other than `about.md`, `features.md`, and the staged
  `pages/.authoring/` reports.
- Never run the page builder or any upload tool; those are the user's steps.
- Every claim must be grounded in the repository. Leave uncertain facts out and
  record them in the guidance.
