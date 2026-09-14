---
name: mod-page-authoring
description: Use when authoring or normalizing the About and Features text for Fuzss Minecraft mod pages, i.e. the files under pages/data/<local id>/about.md and features.md. Covers collecting a source brief, drafting text under pages/.authoring/<local id>/ for review, auditing, and verbatim promotion to pages/data/.
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
   (default `26.2.x`). Derive the local id.
2. Build the authoring brief from the repository root:

   ```sh
   python3 scripts/main/tools/collect_page_brief.py <mod> --branch 26.2.x \
       --out pages/.authoring/<local id>/brief.md
   ```

   Run this from the repository root. From `pages/`, prefix the script path with
   `../`. The collector reads the mods directory from
   `fuzs.multiloader.project.mods`; override with `--mods-root` when needed.
   The collector creates the per-mod directory itself.
3. Dispatch the `page-author` subagent, giving it the brief path, the local id,
   and any curator steer (selling points, must-keep lines, wiki links). It
   writes **drafts only**: `pages/.authoring/<local id>/about.md` and
   `features.md`, plus the working notes at
   `pages/.authoring/<local id>/guidance.md`. It never touches `pages/data/`.
4. Present the drafts for review. The user is the stopgate: apply their edits
   to the drafts, re-running `page-author` or editing directly as instructed.
5. Dispatch the `page-style-auditor` subagent with the draft paths. If it
   reports `FAIL`, fix the drafts and re-run the auditor. Any edit after a
   `PASS` requires a fresh audit.
6. Promote only on explicit user approval ("go ahead", "promote"). Copy the
   passed drafts byte-for-byte to `pages/data/<local id>/`, with no rewording
   and no reformatting:
   - if the drafts omit `features.md` while `pages/data/` has one, ask before
     deleting; default to leaving `pages/data/` untouched and recording it.
   - verify the copies are identical (or carry only the approved omission),
     then re-run the auditor on the `pages/data/` files as a final gate.
7. Report: files promoted, feature count, draft and guidance paths, audit
   verdicts, wiki citations used, curator-kept claims, and any review notes.
   Suggest a commit message naming the mod, feature count, wiki URLs, and kept
   claims, but never commit unless explicitly asked.

## Batch (only when explicitly requested)

Normalization across many mods is a separate, deliberate pass:

1. Read the mod ids from `pages/input`, one per line, ignoring blanks and `#`.
2. Process them in small batches (about ten mods). For each batch, run steps 1-4
   above, one mod at a time, using a fresh `page-author` invocation per mod so
   context stays small. Drafts accumulate under `pages/.authoring/<local id>/`;
   review happens per mod or per batch as the user prefers.
3. Promote each mod only on explicit approval, following step 6.
4. Collect the guidance reports and summarize what manual assets are missing
   across the batch before reporting back.

Do not start a batch unless the user explicitly asks for it.

## Guardrails

- `page-author` never touches `pages/data/`; only promotion writes there, and
  only verbatim passed drafts on explicit approval.
- Never run the page builder or any upload tool; those are the user's steps.
- Mod behavior must come from the repository or the curator's explicit
  direction. Vanilla behavior and Java-vs-Bedrock comparisons may come from
  `minecraft.wiki`, including the framing, with the exact URL plus quoted
  snippet recorded in the guidance. Leave anything else uncertain out and
  record it.
