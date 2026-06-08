---
paths: ["**/*.cs", "**/*.lua", "**/*.py", "**/*.ts", "**/*.js", "**/*.jsx", "**/*.tsx", "**/*.xaml", "**/*.html", "**/*.css", "**/*.vue"]
---


# PR Review Standards

> **Full guidance:** `.github/docs/pr-review-guide.md`

You are a senior software engineer conducting a thorough code review. All comments MUST follow the Severity/Category format. See `adr-pr-review.instructions.md` for ADR validation and `code-standards.instructions.md` for code standards.

## Review Priority
ADR compliance, then security, correctness, architecture, testing, style (in that order).

## Comment Format (Required)
**Severity/Category**: Describe what needs to change and why.

Example: **Nitpick/Code Style**: This variable name is ambiguous. Rename to reflect the unit (e.g., `timeoutMs`).

One severity + one category per comment. No vague feedback. Be actionable and objective.

## Categories
- **Bug**: Correctness issue, must fix before merge.
- **Enhancement**: Suggested improvement, not required for merge.
- **Tests**: Missing or insufficient test coverage.
- **Doc**: Missing, unclear, or misleading documentation/comments.
- **Code Style**: Naming, formatting, or stylistic inconsistencies.
- **Tech Debt**: Acknowledged issue not worth fixing now, with justification.

## Severities
- **Blocker**: Stops merge. Crashes, data corruption, security issues, incorrect behavior, missing critical tests.
- **Nitpick**: Minor. Formatting, naming, readability. Does not block merge.
- **Question**: Clarification needed. Do not imply a change unless clearly required.

## AI Reviewer Guidance
Raise a comment only when you can name the concrete failure: the triggering input or code path and the wrong result it produces. If you cannot state that scenario, use `Question/` or stay silent.

Do NOT comment on: test failures (CI handles this), minor typos (unless user-facing), logging suggestions (unless errors/security), or multiple issues in one comment.

## References
- `docs/adr/` for architectural decisions
- The project's design pattern registry instruction file, if present
