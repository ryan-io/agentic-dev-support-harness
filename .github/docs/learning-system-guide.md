# Learning System Guide

Companion to the learning system summary in the root `README.md`.

## What it solves

Corrections evaporate. You tell the agent to stop doing something, it complies, the session ends, and the next session makes the same mistake. The learning pipeline closes that gap: it watches what actually happens in sessions, detects what you correct repeatedly, and converts the pattern into a proposed instruction-file edit you approve once. After approval, every future session of both agents inherits the fix.

## How it works

A three-stage pipeline runs from hooks registered in `.claude/settings.json`.

`observe.py` records tool calls on every PreToolUse, PostToolUse, and session boundary, appending JSON lines to `.claude/learning/observations.jsonl`. At session end it also parses the session transcript for real user corrections (derived fields only; raw transcript text never enters the log), and a prompt starting with `#correction` flags one explicitly.

`analyze.py` aggregates recurring shapes into instincts, short YAML files carrying a confidence score and a provenance label that keeps real corrections distinct from frequency proxies.

`propose.py` promotes instincts that clear the confidence threshold into markdown proposals naming a specific instruction file and a specific edit, holding back any instinct whose headline is a pattern description rather than an applicable rule.

## Thresholds and staleness

Thresholds live in `.claude/learning/config.json`: 0.7 confidence to promote, 20 observations before analysis runs, correction instincts seeding at 0.45.

Staleness is evidence-based and counts sessions worked, not days elapsed (`adr-learn-replace-wall-clock-decay-with-evidence-based-staleness`): a pending proposal goes stale after 15 sessions without reinforcement and archives at 30 with a recorded reason, instincts decay on the same session clock or archive when their target scope no longer exists, and anything marked `confirmed: true` never decays. A dormant repository loses nothing.

## The human gate

The `continuous-learning` skill is the human gate. Nothing in the pipeline edits an instruction file directly; the skill shows each pending proposal with its evidence and applies it only on your confirmation. It also curates the project-memory digest (see below). Its design is recorded in `adr-learn-establish-shared-project-memory`.

## Solo developers do not need GitHub

The entire loop is local. Hooks fire in your editor, the data lives in `.claude/learning/`, and proposal review happens in a chat session by asking the agent to "review learned patterns". No PR, no remote, no Actions required. A solo dev gets the full benefit from day one on a machine that has never pushed.

The GitHub pieces are team conveniences layered on top. `learning-summary.yml` opens a weekly issue so a team notices proposals nobody has reviewed. `convention-discovery.yml` mines merged PRs for implicit conventions. Both degrade to nothing if you never push; the local pipeline does not depend on them.

The data boundary reflects this. Observations, instincts, and session logs are gitignored and per-developer, because instincts learned from one engineer's workflow should not auto-propagate to teammates. Proposals and `config.json` are committed, because they are the curated output meant for review. Each developer's harness learns locally; the team converges through reviewed proposals.

## Project memory

Approved learning also feeds `.github/instructions/memory.instructions.md`, a committed digest of durable project facts capped at 4,000 characters. It loads on turn one of every session, so the agent starts oriented instead of rediscovering the codebase. The `continuous-learning` skill promotes entries into it from the local session log, under your review, and prunes the least useful entry when it fills. Raw session data stays local; only the curated digest is committed.
