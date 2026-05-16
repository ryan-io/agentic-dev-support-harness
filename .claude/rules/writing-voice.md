---
paths: ["**"]
---


# Writing Voice

> **Full guidance:** `.github/docs/writing-voice-guide.md`

How to write in this project: documentation, agent responses, READMEs, ADR narratives, business-rule descriptions, PR comments, commit messages. Code is governed by `code-standards`; this file governs words.

Use as few words as possible without leaving out critical details. Natural language, not bureaucratic language. Every sentence should earn its place.

## No em dashes
Do not use em dashes. This is a hard rule, not a preference. Use a comma, a colon, parentheses, or a separate sentence instead. The same applies to the en dash used as sentence punctuation; reserve the en dash for numeric ranges.

## Shape of a paragraph
Short. Three or four sentences. One topic per paragraph. Open with the claim, follow with supporting specifics, close.

## Sentence structure
Plain declarative. Subject, verb, object. Sentences vary in length but lean medium-short. Stacked subordinate clauses get broken in two.

First person is normal: "I am writing to recommend," "I have observed." Contractions are fine. The voice is professional but not stiff.

## Specifics
Name things by what they actually are. Be concrete: names, dates, versions, file paths.

## What to cut
Filler transitions, hedge-adverbs, sentences that exist to show the writer is thinking rather than to communicate the thought. If a sentence can be deleted without information loss, delete it.

## Format
Default to flowing paragraphs. Headers and bullets only when the content is genuinely a parallel set of items.

## Agent responses
Agent output follows these same rules. Be direct. If the answer is uncertain, say so and ask rather than guess.

## Scope and exceptions
Applies to human-readable prose. Does not apply to: code comments (terse and technical is fine); generated structured output (JSON, YAML, CSV); lists where the content is genuinely a parallel set; frontmatter and metadata blocks.
