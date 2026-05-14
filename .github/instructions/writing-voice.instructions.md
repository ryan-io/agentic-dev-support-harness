---
applyTo: "**"
---

# Writing Voice
How to write prose deliverables in this project: READMEs, ADR narratives, business-rule descriptions, PR comments, commit messages, documentation. Code is governed by `code-standards`; this file governs words.

Reference: `personal/writing-voice.md` in the author's Obsidian vault.

## No em dashes
Do not use em dashes. They read as an AI tell and the author does not write with them. Use a comma, a colon, parentheses, or a separate sentence instead. A colon introduces a list or an explanation. A comma joins a closely related clause. A period is always available when two thoughts can stand apart. The same applies to the en dash used as sentence punctuation; reserve the en dash for numeric ranges.

## Shape of a paragraph
Short. Three or four sentences, one topic each. Open with the claim, follow with one or two supporting specifics, close. If a paragraph runs past five sentences the next sentence is probably the start of a new paragraph.

## Sentence structure
Plain declarative. Subject, verb, object. Vary length but lean medium-short. Stacked subordinate clauses are a sign to break the sentence in two. First person is normal when writing on the author's behalf. Contractions are fine.

## Specifics
Name things by what they actually are. "C# and C++", not "modern programming languages". "MATLAB scripts to determine root cause failures for testing fixtures", not "analytical scripts". A concrete noun and a date will usually carry more conviction than three adjectives.

## What to cut
Filler transitions ("Moreover," "Furthermore," "It is worth noting that"). Hedge-adverbs ("very," "really," "quite") doing work a specific example would do better. Sentences that exist to show the writer is thinking rather than to communicate the thought.

If you can delete a sentence and lose no information, delete it. If a paragraph opens with "I think" or "It is important to note," delete the opener and keep the rest.

## What's allowed
Standard professional phrases are fine when they fit. "Valuable asset to the team," "strong leader and collaborator," "takes ownership of his work" are reasonable in their place. The goal is clarity and brevity, not novelty or austerity. Avoid them only when they replace a specific that would carry more weight.

## Format
Default to flowing paragraphs. Headers and bullets are tools of last resort, reached for only when the content is genuinely a parallel set of items: checklists, file maps, option enumerations.

## How to apply it
Draft the paragraph version first. On the second pass, cut adverbs and filler transitions. On the third pass, check whether any sentence could be deleted without information loss. If yes, delete it.

## Scope and exceptions
Applies to human-readable prose. Does not apply to: code comments (terse and technical is fine); generated structured output (JSON, YAML, CSV); lists where the content is genuinely a parallel set; frontmatter and metadata blocks.
