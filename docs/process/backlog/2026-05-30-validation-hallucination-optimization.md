# Research: Validation, Hallucination Reduction, and Optimization

Date: 2026-05-30
Status: Draft for review
Scope: This harness (`agentic-dev-support-harness`), grounded in its own mechanisms first.

This note answers three questions in the context of this repository: how robust are its
validations, how does it keep agents from drifting or hallucinating over time, and where
are the optimization opportunities. Each section states what the repo does today, names the
gap, and recommends a concrete next step. External techniques are cited only where they map
onto a real gap.

## What the repo does today (baseline)

The harness has three load-bearing control systems, all currently green (`validate-system.py`
reports 420 PASS, 0 FAIL, 0 WARN as of this date):

1. **Structural validation.** `.github/scripts/validate-system.py` runs 22 check sections:
   file existence, hub sync, the 4,000-char instruction budget, sync-state parity between
   `.github/instructions/` and `.claude/rules/`, cross-reference resolution, skill frontmatter,
   cross-platform script parity, hook-config schema, learning-config schema, Python syntax,
   YAML structure, pipeline-chain integrity, gitignore coverage, agent discoverability, content
   overlap (Jaccard > 0.30 warns), the thin-rules/deep-docs contract, and workflow injection
   safety. It supports an incremental `--changed` mode driven by a `SECTION_MAP`.

2. **Enforcement at the commit boundary.** `.github/hooks/pre-commit` runs sync then validation
   on every commit, hash-skips sync when instruction sources are unchanged, and validates
   incrementally against staged files. Non-zero exit blocks the commit.

3. **Continuous learning.** `observe.py` records tool events to `observations.jsonl`,
   `analyze.py` runs six detectors to mint confidence-scored instinct YAMLs, and `propose.py`
   promotes instincts above 0.7 confidence into human-reviewed proposals. Staleness decay and
   archival keep the corpus from accreting. A developer applies proposals through the
   `continuous-learning` skill. Nothing reaches an instruction file without human review.

The design is deliberate and mature. The recommendations below are additive, not corrective.

## 1. Reliable and robust validations

### Strength

Validation is broad, fast, and enforced. The incremental `SECTION_MAP` and `lru_cache` on
`read_file` keep it cheap enough to run in a pre-commit hook. The checks encode real failure
modes the project has hit before: YAML injection in `save_instinct`, `actions/checkout` version
drift, comma-split handling for multi-value `applyTo`, Windows `python3` breakage. This is a
strong regression net.

### Gap

Every check is **structural**. The validator confirms a file exists, is under budget, is
referenced, and parses. It cannot confirm a rule is **correct, consistent in meaning, or
actually followed**. Three blind spots follow from this:

- **Semantic contradiction.** Two instruction files can each pass every check while telling
  the agent opposite things. Section 19 catches lexical overlap (shared sentences) but not
  conflicting guidance phrased differently.
- **Rule efficacy.** There is no measurement of whether an agent that loads a rule then obeys
  it. The learning pipeline's detector 5 infers non-consultation indirectly, but nothing tests
  the rule against an agent transcript.
- **Template-instance validity.** `adr-pr-review.instructions.md` and `br-review.instructions.md`
  define rich content rules (required sections, no placeholder text, active-voice decisions).
  These are enforced only when an agent or human reviews a PR, never by the automated validator.
  An ADR with an empty `## Decision` would pass `validate-system.py`.

### Recommendation

Add a **second validation tier** that is semantic, kept separate from the structural tier so the
fast pre-commit path stays fast.

- **Codify the ADR/BR content rules as executable checks.** The rules in
  `adr-pr-review.instructions.md` (required `##` sections, reject bracket-placeholder text,
  Status in {Active, Archived}) are already deterministic. Port them to a `validate-content.py`
  that runs on `docs/adr/**` and `docs/business-rules/**`. This needs no model, just regex and
  section parsing, and closes the largest current gap at near-zero cost. This is the
  "executable specification" idea from the ContextCov work: treat instruction files as
  invariants you can run, not just prose you hope is read.
- **Add an LLM-as-judge tier for the parts that genuinely need judgment** (semantic
  contradiction between rules, "is this Decision section vague or generic"). Run it in CI, not
  pre-commit, on changed files only. Current literature puts LLM-judge agreement with human
  reviewers near 85%, above human-to-human agreement, which makes it viable as a gate when you
  control for its known biases: test position bias by swapping argument order and confirming the
  verdict holds, and avoid length/order cues.

Keep tier 1 (structural, every commit), add tier 2 (content regex, every commit, cheap), add
tier 3 (LLM-judge semantic, CI only). Do not collapse them into one slow path.

## 2. Reducing hallucinations over time

### Strength

The harness already attacks the highest-leverage cause of agent error in a repo: **stale or
ungrounded instructions**. `pattern-fidelity.instructions.md` forces precedent-checking before
inventing a pattern, `research.instructions.md` requires primary sources and dated facts,
`agent-guardrails.md` codifies "Ask, Do Not Guess." The learning loop's decay and human-gated
promotion stop low-quality instincts from hardening into rules. This is closer to drift control
than classic factual hallucination control, and for a coding-support harness that is the right
target.

### Gap

There is no **runtime grounding or verification step**. The controls are all upstream (good
rules) or downstream (post-hoc review). Nothing checks an agent's output against the repo at the
moment of generation. Specifically:

- **No sub-file retrieval grounding.** Rules are loaded by file-glob scope, which is correct at
  the file level: an agent editing a `.cs` file *should* get `csharp-code-standards`, and the
  glob delivers exactly that. The limitation is granularity. The `applyTo`/`paths` frontmatter is
  a file-level on/off switch with no finer setting, so it cannot say "load this only when a new
  abstraction is being introduced" or "only for the region being edited." The over-firing case is
  the `**`-scoped universal rules (`pattern-fidelity`, `agent-guardrails`), which load on every
  edit regardless of whether the change actually involves a pattern or a risky operation. See the
  appended resource list for whether sub-file granularity is even achievable.
- **No self-verification loop.** There is no equivalent of the generate -> plan verification ->
  answer independently -> revise pattern that current research credits with large hallucination
  reductions. The agent's claims about the codebase are not cross-checked against the codebase
  before they land.
- **No citation/attribution enforcement at runtime.** `research.instructions.md` asks for an
  evidence trail in prose, but nothing verifies that file paths and links an agent cites
  actually resolve. The structural validator checks cross-references in *committed* docs, not in
  an agent's *response*.

### Recommendation

- **Add a lightweight grounding check to the highest-risk skills.** For skills that assert facts
  about the codebase (`system-review`, `convention-discovery`, anything producing an ADR), add a
  final step: re-read every file path and symbol the output names and confirm it exists before
  finalizing. This is the cheapest, highest-yield verification step and needs no new
  infrastructure, just a skill instruction. It directly enforces the existing
  `research.instructions.md` evidence-trail rule.
- **Reuse the validator's cross-reference logic on agent output.** Section 5 of
  `validate-system.py` already resolves backtick-wrapped paths. Extract it into a reusable
  function and let skills call it on their own drafts. A claim that cites a non-existent file is
  the most detectable form of hallucination in this domain; catch it deterministically rather
  than hoping review finds it.
- **Move from glob-scoped to relevance-scoped rule loading (longer term).** The
  instruction-tool-retrieval approach (retrieve only the minimal rule fragments a step needs)
  reports large context savings and better routing. That is a bigger change than this repo needs
  today, but the detector-5 signal (rules edited-in-scope yet never consulted) is already the
  evidence that pure glob-scoping mis-targets. Treat it as a direction, not an immediate task,
  and require an ADR before adopting it.

A caution consistent with `pattern-fidelity`: do not bolt on RAG, embeddings, or a multi-agent
verifier because the literature praises them. This repo's hallucination surface is small and
mostly addressed by grounding rules. The self-check step above is proportional; an embedding
index is not, yet.

## 3. Possible optimizations

### Already done

The repo has clearly invested here: incremental validation (`SECTION_MAP`), cached file reads
(`lru_cache`), hash-based sync skipping in the pre-commit hook, incremental observation
processing (analysis markers), observation-file rotation at 1,000 entries, and propose.py firing
only when new instincts appear. The obvious wins are taken.

### Remaining opportunities

- **Context budget efficiency, not just file-size budget.** The 4,000-char limit caps each file
  but not the *total* an agent loads. Every universal rule (`**` scope) loads on every file.
  Five core instruction files plus the hub load unconditionally. Measure the real token cost of
  a cold agent start, then ask the context-engineering question directly: does each universal
  rule earn its permanent place, or could some move to on-demand guides behind a "Full guidance"
  directive (the thin-rules/deep-docs contract already exists for exactly this). Detector 6
  already tracks guide-consultation misses, so the signal to tune this is being collected.
- **Close the learning loop's measurement gap.** The pipeline detects patterns and proposes
  rules but never measures whether an applied rule changed agent behavior. Add a before/after
  signal: when a proposal is applied, tag subsequent observations so the next analysis run can
  report whether the targeted correction rate dropped. Without this, the loop optimizes for
  proposal volume, not outcome.
- **Validator self-coverage.** `validate-system.py` is now 1,197 lines and is itself load-bearing
  and unprotected by tests. The project's own `code-standards` rule requires tests for new logic.
  A small fixture-based test suite (a known-broken repo snapshot that should FAIL specific
  sections, a known-good one that should PASS) would catch validator regressions, which are
  currently invisible until they let a real defect through.
- **Parallelize CI tiers.** If the tier-2/tier-3 content and semantic checks are added, run them
  as separate CI jobs from the structural validator so total wall-clock does not grow linearly
  with check count.

## Suggested priority order

1. `validate-content.py` for ADR/BR content rules (cheap, closes the biggest validation gap).
2. Grounding self-check step in fact-asserting skills (cheap, closes the biggest hallucination gap).
3. Fixture tests for `validate-system.py` (protects the protector).
4. Context-budget audit of universal rules (measure first, then trim).
5. Outcome measurement in the learning loop (turns the loop from open to closed).
6. LLM-as-judge semantic tier and relevance-scoped loading (larger, ADR-gated, later).

Items 1 to 3 need no new dependencies and no architectural change, so they do not require an
ADR. Items 5 and 6 introduce new cross-cutting mechanisms and should be proposed as ADRs per
`agent-guardrails`.

## Sources

External techniques referenced above:

- [ContextCov: Deriving and Enforcing Executable Constraints from Agent Instruction Files](https://arxiv.org/pdf/2603.00822)
- [Dynamic System Instructions and Tool Exposure for Efficient Agentic LLMs (instruction-tool retrieval)](https://arxiv.org/pdf/2602.17046)
- [Effective Context Engineering for AI Agents](https://tianpan.co/blog/2026-02-23-effective-context-engineering-for-ai-agents)
- [LLM-as-a-Judge: The Complete Guide (Confident AI)](https://www.confident-ai.com/blog/why-llm-as-a-judge-is-the-best-llm-evaluation-method)
- [When AIs Judge AIs: Agent-as-a-Judge Evaluation](https://arxiv.org/pdf/2508.02994)
- [Gaming the Judge: Unfaithful Chain-of-Thought Can Undermine Agent Evaluation](https://arxiv.org/pdf/2601.14691)
- [Reducing Hallucinations in LLM-Generated Code via Semantic Triangulation](https://arxiv.org/pdf/2511.12288)
- [LLM Hallucination Detection and Mitigation: Best Techniques (Maxim)](https://www.getmaxim.ai/articles/llm-hallucination-detection-and-mitigation-best-techniques/)

Repo evidence: `validate-system.py` (run output 420/0/0), `.github/scripts/learning/{observe,analyze,propose}.py`,
`.github/hooks/pre-commit`, `.github/instructions/{adr-pr-review,br-review,pattern-fidelity,research}.instructions.md`,
`.github/docs/system-index.md`, `.claude/learning/config.json`.

---

# Appendix: Retrieval Grounding at Sub-File Granularity

Added 2026-05-30 in response to a focused question: is there a supported mechanism for more
granular retrieval, specifically loading a rule only when a specific pattern *within* a file is
present, or only when a specific *region* of a file is being edited?

## Direct answer

The frontmatter abstraction does not support sub-file granularity. Both runtimes this harness
targets treat the loading condition as a file-level switch:

- **Copilot / VS Code (`applyTo`).** The glob is the on/off switch and nothing finer. If the
  glob matches the file, the whole instruction file loads; matching files stack (union, no
  override). There is no syntax for "within the file" or "for this edit region." This is correct
  for `csharp-code-standards` -> `*.cs`: file-type is exactly the right grain there. It cannot
  express intent- or region-conditional loading.
- **Claude (`paths`).** Same model: directory/glob scope, file-level granularity.

So the granularity ceiling of the declarative layer is the file. To go below it you leave
frontmatter and move to one of three escalating mechanisms.

## The three layers that go below file-level

**Layer 1: Agent-decided (semantic-description) loading.** Cursor's `.mdc` rules add a mode the
markdown-frontmatter formats lack: `alwaysApply: false` with a `description` and no globs. The
agent reads the description and decides whether to pull the rule in, based on the task rather than
the file path. This is the closest thing to "load only when a specific *pattern of work* is
happening" (e.g. load `pattern-fidelity` only when the task is introducing an abstraction). It is
intent-conditional, not region-conditional, and it trades determinism for relevance: the agent
might judge wrong. This harness does not target Cursor, but the pattern is portable, a rule's
frontmatter can carry a description and a skill can gate its own loading on relevance.

**Layer 2: Hook-based conditional injection (programmable, content-aware).** This is the real
answer for "load only when a specific pattern within the file is detected." Claude Code
`PreToolUse` hooks receive the tool input (including `file_path` and, for edits, the target
content) on stdin and can return `additionalContext` to inject rules conditionally. A hook can
read the file, detect a pattern (a raw SQL string, a new `class` declaration, a `TODO`), and
inject only the matching rule. The harness already runs this exact machinery: `observe.py` is a
`PreToolUse`/`PostToolUse` hook that parses `tool_input` and extracts `file_path`, extension, and
a command summary. Extending an observe-style hook from *recording* to *injecting* is the
in-repo, supported path to content-conditional loading. Granularity here is whatever the hook can
compute: file content, yes; precise edit region, only partially (the hook sees the Edit tool's
`old_string`/`new_string`, so it knows the region being changed, not arbitrary cursor position).

**Layer 3: Code-aware RAG (AST / region-level retrieval).** For true region- and symbol-level
grounding, the research field is code-aware retrieval-augmented generation: chunk the codebase by
AST structure rather than line windows, retrieve the fragments relevant to the symbol or region
in play, and compose context from coarse (file/module) and fine (function/region) pools. This is
the heaviest option, needs an index and an embedding/graph store, and is disproportionate to this
harness's small instruction corpus. It is the right reference if the question ever shifts from
"which *rules* to load" to "which *code context* to ground an edit in."

## Mapping to this repo

The honest conclusion for this harness: the declarative file-level glob is correct and should
stay for file-type rules. The only place sub-file granularity earns its complexity is the handful
of `**`-scoped universal rules that over-fire. The proportional mechanism for those is Layer 2, a
content-aware `PreToolUse` hook, because the repo already runs hooks of exactly that shape and it
keeps determinism. Layer 1 (semantic description) is a lighter alternative if the harness ever
targets Cursor or lets skills self-gate. Layer 3 is out of scope until the problem becomes code
retrieval rather than rule selection. Any of these is a new cross-cutting mechanism and needs an
ADR per `agent-guardrails`.

## Annotated resources

Mechanism references (how loading actually works):

- [Use custom instructions in VS Code (official)](https://code.visualstudio.com/docs/copilot/customization/custom-instructions): primary source confirming `applyTo` is glob/file-level; stacking, no override. Establishes the granularity ceiling for the Copilot side.
- [Instruction File Format and Frontmatter (awesome-copilot / DeepWiki)](https://deepwiki.com/github/awesome-copilot/4.2-instruction-file-format-and-frontmatter): concise reference on the frontmatter fields and that omitting `applyTo` makes a file inert until manually attached.
- [Claude Code Hooks reference (official)](https://code.claude.com/docs/en/hooks): primary source for `PreToolUse`, `additionalContext`, and the stdin event schema. This is the Layer-2 mechanism the harness can extend.
- [Claude Code: Using Hooks for Guaranteed Context Injection](https://dev.to/sasha_podles/claude-code-using-hooks-for-guaranteed-context-injection-2jg): worked example of a `PreToolUse` hook reading `file_path` from stdin and injecting package-specific rules. Directly models content-conditional injection.
- [Cursor Rules (official docs)](https://cursor.com/docs/rules): documents the four activation modes, including agent-decided (`alwaysApply: false` + `description`, no globs). The Layer-1 reference for intent-conditional loading.
- [AGENTS.md vs CLAUDE.md vs Cursor Rules vs Copilot (2026)](https://codersera.com/blog/agents-md-vs-claude-md-vs-cursor-rules-comparison-2026/): side-by-side of the loading semantics across all four formats; useful for seeing exactly where each one tops out on granularity.

Sub-file / region-aware retrieval (Layer 3, code-aware RAG):

- [cAST: Enhancing Code RAG with Structural Chunking via Abstract Syntax Tree](https://arxiv.org/html/2506.15655v1): AST-based chunking that preserves syntactic units instead of line windows. The core technique if region-level grounding is ever needed.
- [CAST (CMU)](https://www.cs.cmu.edu/~sherryw/assets/pubs/2025-cast.pdf): companion/primary write-up of structural chunking for code retrieval.
- [Retrieval-Augmented Code Generation: A Survey with Focus on Repository-Level Approaches](https://arxiv.org/html/2510.04905v1): survey covering sparse/dense/graph retrieval and fine-grained local vs coarse global context composition (R2C2-Coder, A3-CodGen). Good map of the field before committing to any one approach.
- [Code-aware RAG: Fundamentals, Advancements, and Future Directions](https://atoms.dev/insights/code-aware-retrieval-augmented-generation-fundamentals-advancements-and-future-directions/66c660d42f7b4119835309cbb771a852): accessible overview of graph/AST-based retrieval for those evaluating whether Layer 3 is worth it.

Instruction-level retrieval (the middle ground, retrieve rule fragments not whole files):

- [Dynamic System Instructions and Tool Exposure for Efficient Agentic LLMs](https://arxiv.org/pdf/2602.17046): instruction-tool retrieval: fetch only the minimal system-prompt fragments a step needs. The technique behind "load less of a rule, not just fewer rules."
- [ContextCov: Deriving and Enforcing Executable Constraints from Agent Instruction Files](https://arxiv.org/pdf/2603.00822): treats instruction files as executable specs; relevant to making conditional loading verifiable rather than hoped-for.
