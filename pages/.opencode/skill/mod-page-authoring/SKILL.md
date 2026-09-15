---
name: mod-page-authoring
description: Use when authoring or normalizing the About and Features text for Fuzss Minecraft mod pages, i.e. the files under pages/data/<local id>/about.md and features.md. Covers collecting a source brief, drafting text under pages/.authoring/<mod>/ for review, auditing, and verbatim promotion to pages/data/.
---

# Mod page authoring

This skill drives the text pipeline for the `pages/` subtree. It produces
exactly two files per mod: `pages/data/<local id>/about.md` and
`features.md`. Images, `sections`, `credits.md`,
`configuration.md`, and anything under `commons/` are manual and out of scope.
Installation is fully derived from `metadata.json`; there is no manual file for it.

The writing standard is `pages/AGENTS.md`; read it before starting.
`<local id>` is the mod repository name with dashes removed (`air-hop` ->
`airhop`).

## Single mod

1. Pick the repository name (e.g. `eternal-nether`) and the branch
   (default `26.2.x`). The staging directory uses the repository name as-is;
   the `pages/data/` directory uses the local id (dashes removed).
2. Build the authoring brief from the repository root:

   ```sh
   python3 scripts/main/tools/collect_page_brief.py <mod> --branch 26.2.x \
       --out pages/.authoring/<mod>/brief.md
   ```

   Run this from the repository root. From `pages/`, prefix the script path with
   `../`. The collector reads the mods directory from
   `fuzs.multiloader.project.mods`; override with `--mods-root` when needed.
   The collector creates the per-mod directory itself.
3. Dispatch the `page-author` subagent, giving it the brief path, the mod id,
   and any curator steer (selling points, must-keep lines, wiki links). It
   writes **drafts only**: `pages/.authoring/<mod>/about.md` and
   `features.md`, plus the working notes at
   `pages/.authoring/<mod>/guidance.md`. It never touches `pages/data/`.
4. Relay the author's full report to the user inline — open questions first,
   then the draft About and Features in fenced markdown blocks, then the
   guidance. Do not just point at file paths. The user is the stopgate: on
   their feedback, resume the same `page-author` session with that feedback and
   relay the revision diff it returns.
5. Dispatch the `page-style-auditor` subagent with the draft paths and relay
   its verdict and violations inline. If it reports `FAIL`, fix the drafts and
   re-run the auditor. Any edit after a `PASS` requires a fresh audit.
6. Promote only on explicit user approval ("go ahead", "promote"). Copy the
   passed drafts byte-for-byte to `pages/data/<local id>/`, with no rewording
   and no reformatting:
   - if the drafts omit `features.md` while `pages/data/` has one, ask before
     deleting; default to leaving `pages/data/` untouched and recording it.
   - verify the copies are identical (or carry only the approved omission),
     then re-run the auditor on the `pages/data/` files as a final gate.
7. Report inline: files promoted, feature count, audit verdicts, wiki citations
   used, curator-kept claims, and any review notes. Suggest a commit message
   naming the mod, feature count, wiki URLs, and kept claims, but never commit
   unless explicitly asked.

## Batch (only when explicitly requested)

Normalization across many mods is a separate, deliberate pass:

1. Read the mod ids from `pages/input`, one per line, ignoring blanks and `#`.
2. Process them in small batches (about ten mods). For each batch, run steps 1-3
   above, one mod at a time, using a fresh `page-author` invocation per mod so
   context stays small. Drafts accumulate under `pages/.authoring/<mod>/`;
   review happens per mod or per batch as the user prefers.
3. After a batch, report a compact table: mod, feature count, whether Features
   were omitted, missing manual assets, and open questions. Do not paste every
   mod's drafts; expand a single mod's full report only when the user asks.
4. Promote each mod only on explicit approval, following step 6.

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
