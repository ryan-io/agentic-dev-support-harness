# PR Review Guide

Companion to `pr-review.instructions.md`. Read this before conducting a code review.

## Review Priority Rationale

Review in this order. Earlier items block merge; later items improve quality.

1. **ADR Compliance**: PR must not violate any ADR under `docs/adr/`. Architectural decisions are load-bearing constraints, not suggestions.
2. **Security**: Exposed secrets, unvalidated input, authentication gaps. A security issue is always a blocker.
3. **Correctness**: Logic errors, race conditions, data integrity. The code must do what it claims.
4. **Architecture**: Pattern violations, dependency management, layering concerns. Structural problems compound over time.
5. **Testing**: Missing coverage for new logic, improper mocking. Untested code is unverified code.
6. **Style**: Naming, formatting, readability. Important but never blocks a merge.

## AI Reviewer Extended Guidance

Prefer **Question/** when uncertain. Use **Blocker/** only when confident. The cost of a false positive blocker (blocks a correct PR, wastes developer time) is higher than the cost of a missed nitpick.

Never combine multiple categories in one comment. Each issue gets its own comment with one severity and one category. Avoid speculative language: "this might cause..." is weaker than "this causes... when..." with a concrete scenario.

AI comments are held to the same quality bar as human reviews. If you would not stake your reputation on the comment, do not post it.

## Comment Format: Re-review Rules

On re-review, reply "Still an issue." or "Resolved." to your original comment. Do not duplicate the comment or create a new thread for the same issue.
