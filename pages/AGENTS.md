# AGENTS.md

Instructions for agents working in the `pages/` subtree (mod page content).
This file defines the canonical writing standard for the `About` and `Features`
sections. Repository-wide guidance lives in `../AGENTS.md`.

## Scope

The text pipeline owns exactly two files per mod:

- `data/<local id>/about.md`
- `data/<local id>/features.md`

`<local id>` is the mod id with dashes removed (`air-hop` -> `airhop`). Everything
else in `data/<local id>/` and `commons/` is maintained manually: images
(`banner.png`, `logo.png`, `strip.png`, `media/`), `credits.md`, `configuration.md`,
`installation.yaml`, `sections.yaml`, and `socials.yaml`.

This is a writing guide, not a page generator. Rendering the pages and
publishing them are handled outside this repository.

## Audience and voice

- Write for players, not developers.
- Lead with what the mod does, why it is useful, and what makes it stand out.
- Be concise, modern, and benefit focused. Light enthusiasm is welcome;
  marketing fluff and exaggerated claims are not.
- Use American English (`color`, `customize`, `armor`).
- Prefer plain sentences over formatting. Only use `**bold**`, `code`, and links
  where they carry meaning.
- Never repeat information between the About and Features sections.

## About

- Usually 2 to 3 short paragraphs. Scale down to a single paragraph for small
  utility mods and up to 3 for large content mods. Never pad.
- Write the mod name in **bold exactly once**, at the start of the first
  paragraph. Refer to it as "the mod" or "this mod" afterwards.
- Focus on purpose, value, and identity: what the mod adds and why a player
  would want it.
- Mention only the standout features. Do not turn About into prose that mirrors
  the Features list.
- Use at most one fitting emoji per paragraph, inside a sentence, to emphasize a
  benefit (for example "millions of colors 🎨" or "perform significantly better 🚀").
  Never place an emoji at the start of a paragraph.
- Avoid implementation details unless they are the selling point (for example a
  performance improvement).

## Features

- Only include Features when the mod has enough meaningful functionality to
  justify them. It is fine to omit `features.md` entirely for small mods.
- Always use one flat list. Do not add bold group headings or nested lists.
- Format every bullet as:

  ```markdown
  * 🚀 **Feature Name:** Explanation.
  ```

- Aim for 3 to 5 meaningful features for small and quality-of-life mods, and up
  to roughly 10 to 12 for large content mods. Prefer the strongest features over
  completeness.
- Order features from most important to least important.
- Use a fitting emoji as a visual anchor on each feature.
- Include only features that help define or sell the mod. Exclude mundane
  details, crafting recipes, mod loader support, technical implementation, and
  every available option.
- Summarize configuration and compatibility as a capability when relevant,
  never as a list of individual settings.
- Mention integrations with other mods only when they add significant value.

## Grounding

Only state facts that can be derived from the mod repository. Acceptable
sources: `gradle.properties`, `metadata.json`, `README.md`, `CHANGELOG.md`,
`@Config(description = ...)` strings, language files, and the source tree.

- Do not invent features, numbers, or names.
- Do not claim compatibility, performance, or behavior that the repository does
  not support.
- If a fact is uncertain, leave it out and record it in the review notes.

## Pipeline

Text is produced by a deterministic collector plus two subagents:

- `scripts/main/tools/collect_page_brief.py` builds a normalized authoring brief.
- `.opencode/agent/page-author.md` writes `about.md` and `features.md`.
- `.opencode/agent/page-style-auditor.md` checks finished text against this file.
- `.opencode/skill/mod-page-authoring/SKILL.md` describes the end-to-end workflow.

Briefs and guidance are staged under `pages/.authoring/` and never written into
`pages/data/`.
