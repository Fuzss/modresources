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
`sections`, and `socials`.

This is a writing guide, not a page generator. Rendering the pages and
publishing them are handled outside this repository.

## Audience and voice

- Write for players, not developers.
- Lead with what the mod does, why it is useful, and what makes it stand out.
- Be concise, modern, and benefit focused. Light enthusiasm is welcome;
  marketing fluff and exaggerated claims are not.
- Use American English (`color`, `customize`, `armor`).
- Write the names of items, blocks, mobs, and mod features as common nouns in
  running text, following the Minecraft Wiki (write "an eye of ender", "a mutant
  zombie", "the hulk hammer", not "Eye of Ender", "Mutant Zombie", "Hulk
  Hammer"). Capitalize only proper nouns such as the Nether, the End, the
  Overworld, Java Edition, Bedrock Edition, and the mod's own name.
- Prefer plain sentences over formatting. Only use `**bold**`, `code`, and links
  where they carry meaning.
- About and Features may cover the same topics at different resolution: About
  frames them in prose, Features lists the specifics. Do not restate a Features
  bullet in the same words.

## About

- Usually 3 short paragraphs of roughly 25 to 45 words each (2 to 3 sentences),
  aiming for about 90 to 110 words total. Use fewer for very small mods; never
  pad. A paragraph may cover more than one related idea.
- Three shapes that read well across existing pages: what it is -> how it plays
  -> the payoff; what it is -> concrete examples and variety -> how far it
  extends; what it is -> how it lifts the vanilla experience -> the feel and
  polish it adds.
- Write the mod name in **bold exactly once**, in the first paragraph. An
  opening hook sentence may come before it; refer to it as "the mod" or "this
  mod" afterwards.
- Focus on purpose, value, and identity: what the mod adds and why a player
  would want it.
- Name standout capabilities. Leave step-by-step mechanics, exhaustive lists
  (interactions, items, settings), and per-setting details out of About;
  Features states each capability concisely rather than walking through it.
- Configuration and compatibility may appear as a capability or as part of the
  payoff; keep the individual settings in Features.
- Use emojis sparingly to emphasize standout features or benefits in or at the
  end of a sentence — for example "millions of colors 🎨" or "perform
  significantly better 🚀". Each emoji must be anchored to the feature or
  benefit it marks in the same sentence; tagging named capabilities ("Dye
  frames in millions of colors 🎨") is the intended use. A sentence-trailing
  emoji goes after the terminal punctuation ("...active players. 🐄", not
  "...active players 🐄."). Never scatter emojis over generic sentences or
  closers, and never place an emoji at the start of a paragraph.
- Avoid implementation details unless they are the selling point (for example a
  performance improvement).

## Features

- Only include Features when the list adds information the About does not. If
  the mod does one thing and the About already says it, omit `features.md`
  entirely rather than restating the same point as bullets.
- Always use one flat list. Do not add bold group headings or nested lists.
- Format every bullet as:

  ```markdown
  * 🚀 **Feature Name:** Explanation.
  ```

- Write feature names in Title Case, lowercasing short connectors (a, an, and,
  or, of, the, for, to, in, on, with): "Custom Wind and Motion", not "Custom
  Wind And Motion".
- Keep each bullet to one capability in one or two short sentences, roughly 10
  to 20 words; existing pages average about 15. If a bullet covers several
  distinct capabilities, split it into separate bullets; if it is one capability
  padded with mechanics, trim it. A bullet that enumerates examples of a single
  capability may run a little longer.
- Aim for 5 to 8 meaningful features for most mods, and up to roughly 20 for
  large content mods; splitting multi-capability bullets is the normal way to
  reach a higher count. These are guidance, not limits: a list is done when
  every major player-facing selling point is covered and nothing padding
  remains. Prefer the strongest features over completeness.
- Order features from most important to least important.
- Use a fitting emoji as a visual anchor on each feature.
- Include only features that help define or sell the mod. Exclude mundane
  details, crafting recipes, mod loader support, technical implementation, and
  every available option.
- Summarize configuration and compatibility as a capability when relevant,
  never as a list of individual settings.
- Mention integrations with other mods only when they add significant value.

## Grounding

State only facts that can be derived from the mod repository, from the
curator's explicit direction, or from vanilla context cited below. Acceptable
sources: `gradle.properties`, `metadata.json`, `README.md`, `CHANGELOG.md`,
`@Config(description = ...)` strings, language files, the source tree, the
curator's review steer, and `minecraft.wiki` for vanilla behavior and
Java-vs-Bedrock comparisons only (including the framing of such a comparison),
and its style guide for naming and capitalization.

- Do not invent features, numbers, or names.
- Do not claim compatibility, performance, or behavior that the repository does
  not support.
- Record the exact wiki URL plus the quoted snippet in the guidance whenever a
  comparison relies on it.
- If a fact is uncertain, leave it out and record it in the review notes.

## Continuity

Existing page text is a first-class input. Inventory every claim in the current
`about.md` and `features.md`: keep, repair, or drop each one, and record the
decision in the guidance. Never silently drop a lead claim (the About opening,
the first Features bullet); every drop needs a justification.

## Pipeline

Text is produced by a deterministic collector plus two subagents, with the user
as the review stopgate:

1. `pages/tools/collect_page_brief.py` builds a normalized brief at
   `pages/.authoring/<mod>/brief.md`.
2. `pages/.opencode/agent/page-author.md` drafts `about.md` and `features.md`
   under `pages/.authoring/<mod>/` only. It never writes `pages/data/`.
3. The user reviews the drafts and requests changes; the author revises them.
4. `pages/.opencode/agent/page-style-auditor.md` checks the drafts against this
   file. Only `PASS` drafts are promoted.
5. On explicit approval, the drafts are copied verbatim to
   `pages/data/<local id>/`.
6. `pages/.opencode/skill/mod-page-authoring/SKILL.md` describes the end-to-end
   workflow.

Briefs, drafts, and guidance are staged under `pages/.authoring/` (ignored) and
never written into `pages/data/` except by verbatim promotion.
