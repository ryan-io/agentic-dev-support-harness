---
applyTo: "**"
---

# Writing Voice
How to write prose deliverables in this project: READMEs, ADR narratives, business-rule descriptions, PR comments, commit messages, documentation. Code is governed by `code-standards`; this file governs words.

## No em dashes
Do not use em dashes. This is a hard rule, not a preference. They read as an AI tell and the author does not write with them. Use a comma, a colon, parentheses, or a separate sentence instead. A colon introduces a list or an explanation. A comma joins a closely related clause. A period is always available when two thoughts can stand apart. The same applies to the en dash used as sentence punctuation; reserve the en dash for numeric ranges.

## Shape of a paragraph
Short. Three or four sentences. One topic per paragraph. Open with the claim, follow with one or two supporting specifics, close. When a paragraph hits five sentences the next thought is probably its own paragraph.

## Sentence structure
Plain declarative. Subject, verb, object. Sentences vary in length but lean medium-short. Stacked subordinate clauses get broken in two.

First person is normal: "I am writing to recommend," "I have observed," "I strongly recommend." Contractions are fine. The voice is professional but not stiff.

## Specifics
Name things by what they actually are. "C# and C++", not "modern programming languages". "MATLAB scripts to determine root cause failures for testing fixtures", not "analytical scripts". "Leading Self Program in 2018", not "a recognized leadership program."

A concrete noun and a date will usually carry more conviction than three adjectives.

## What to cut
Filler transitions: "Moreover," "Furthermore," "It is worth noting that." Hedge-adverbs that try to do work a specific should do: "very," "really," "quite." Sentences that exist to show the writer is thinking rather than to communicate the thought.

If a sentence can be deleted without information loss, delete it. If a paragraph opens with "I think" or "It is important to note," delete the opener.

## What's allowed
Standard professional phrases are fine when they fit. "Valuable asset to the team," "strong leader and collaborator," "takes ownership of his work" are reasonable in their place. The goal is clarity and brevity, not novelty or austerity. Avoid them only when they replace a specific that would carry more weight.

## Format
Default to flowing paragraphs. Headers and bullets are tools of last resort, reached for only when the content is genuinely a parallel set of items: checklists, file maps, option enumerations.

## Conversational style
In informal contexts (chat, casual notes, PR comments) the voice drops formality. Functional, not decorative. Don't replicate typos in formal output, but match the directness. Short, lowercase sentence openers are fine in chat. In formal deliverables, standard capitalization applies.

## How to apply it
Draft the paragraph version first. On the second pass, cut adverbs and filler transitions. On the third pass, ask of each sentence whether it could be deleted without losing information. If yes, delete it. The pattern is brevity through deletion, not through compression.

## Scope and exceptions
Applies to human-readable prose. Does not apply to: code comments (terse and technical is fine); generated structured output (JSON, YAML, CSV); lists where the content is genuinely a parallel set; frontmatter and metadata blocks.
