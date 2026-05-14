---
paths: ["**"]
---


# Writing Voice
How to write prose deliverables in this project — READMEs, ADR narratives, business-rule descriptions, PR comments, commit messages, documentation. Code is governed by `code-standards`; this file governs words.

Reference: `personal/writing-voice.md` in the author's Obsidian vault (derived from a recommendation letter Ryan authored).

## What the voice does
- **Direct and substantive.** Every sentence earns its place. No throat-clearing intros, no hedging qualifiers, no "in conclusion" wrap-ups. If a sentence could be deleted without losing information, delete it.
- **Specifics over abstractions.** Name the concrete thing rather than its label. "The pre-commit hook regenerates the mirror" beats "Synchronization is automatically managed."
- **Warm but not effusive.** Regard comes through in what is observed, not in stacked adjectives. Avoid "incredible," "amazing," "phenomenal."
- **Professional plain speech.** First person when appropriate. Contractions are fine. Sentences vary in length but lean medium-short. Paragraphs are dense, not bullet-listed.

## What the voice avoids
- Fluff transitions ("Moreover," "Furthermore," "It is worth noting that").
- Marketing-speak and superlatives without evidence.
- Heavy formatting. Headers and bullets are tools of last resort, not the default. Prefer paragraphs.
- Hedge-adverbs ("very," "really," "quite") that try to do work a concrete example should be doing.
- Sentences that exist to make the writer sound thoughtful rather than to convey thought.

## How to apply it
Default to flowing paragraphs. Reach for a header or a list only when the content is genuinely a parallel set of items. Cut adverbs aggressively on the second pass. If a sentence opens with "I think" or "It is important to note," delete the opener and keep the rest.

Read each paragraph and ask: would I lose information by deleting this? If not, delete it.

## Scope and exceptions
This applies to human-readable prose. It does not apply to:
- Code comments (terse and technical is fine).
- Generated structured output (JSON, YAML, CSV).
- Lists where the content is genuinely a parallel set — checklists, file maps, option enumerations.
- Frontmatter and metadata blocks.

When in doubt, write the paragraph version first and convert to a list only if the result reads worse.
