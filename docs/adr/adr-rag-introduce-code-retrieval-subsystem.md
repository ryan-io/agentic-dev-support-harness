# ADR-RAG: Introduce Code Retrieval Subsystem

---

## Metadata

| Field   | Value      |
|---------|------------|
| Status  | Proposed   |
| Date    | 2026-05-30 |
| Authors | @ryan-io   |

---

## Context

Agents in consumer projects have no structured way to locate relevant code. Without it, an agent loads entire files or guesses with glob patterns. Both waste tokens and pull in irrelevant context.

The harness already loads instruction files on demand via glob-scoped frontmatter. That works for a small prose corpus. It does not work for application code, where the relevant unit is a function or type region, not a whole file.

Retrieval precision and simplicity conflict. Fine-grained AST chunking improves precision but requires an index. Coarser strategies are easier to maintain but load too much. The subsystem must reduce context bloat without introducing an index that fails silently.

The subsystem must be composable and on-demand, not always-on infrastructure. A retrieval miss that forces full-file fallback costs more tokens than having no subsystem at all.

Building the index is not free. Parsing is fast; embedding generation is slow and rate-limited. A 50k-line codebase can take several minutes on a cold build. That cost repeats on any full rebuild.

Index update cadence is a design decision with real tradeoffs. Rebuilding on every merge to main is simple but pays full cost on every PR. Incremental updates (re-indexing only changed files) are cheaper but break on cross-cutting refactors: a renamed interface touching twenty files leaves nineteen stale if only the changed file is re-indexed. Agent-triggered on-demand rebuilds stay current during development but add query-time latency. The right choice depends on codebase size and merge frequency and must be decided per consumer project before production use.

Tree-sitter and BM25 plus dense embedding hybrid retrieval are the leading candidates. Research is ongoing. This ADR records the forces so implementation can proceed incrementally.

---

## Decision

We propose a code retrieval subsystem as a composable harness feature, parallel to the continuous-learning pipeline. It targets application code in consumer projects, not the harness instruction corpus.

The approach is AST-aware chunking via tree-sitter combined with BM25 plus embedding hybrid retrieval. Tree-sitter splits files at semantic boundaries (function definitions, class bodies) and prepends the enclosing scope as a header on each chunk. BM25 handles exact symbol matches; dense embeddings handle semantic similarity. Reciprocal rank fusion combines scores at query time.

Flat line-window chunking splits mid-function and was rejected. Embedding-only retrieval misses exact identifiers. Full-file loading is accurate but token-inefficient. The hybrid trades index maintenance cost for precise, lean retrieval.

Status is Proposed pending the comparative research spike.

---

## Other Considerations

**AST chunking alone (no retrieval layer)**

Tree-sitter can serve chunks directly without a retrieval index, which removes the vector store, embedding model, and freshness concerns. The problem is selection: without retrieval, the agent loads all chunks for a file or names the file explicitly. This degrades as the codebase grows. AST chunking is a preprocessing step, not a standalone solution; it is a component of the chosen approach.

**BM25 alone**

BM25 handles exact symbol lookups cheaply with no embedding infrastructure. It fails on semantic queries and on chunks that split mid-function when using flat line windows. It is a viable fallback when the full pipeline is unavailable, not a primary strategy.

**Dense embedding retrieval alone**

Embeddings handle semantic queries and are language-agnostic. They blur exact token boundaries, missing precise identifier matches. They also carry the same chunk-quality problem as flat BM25 without AST splitting. Embeddings are a necessary complement to BM25 in the hybrid, not a replacement.

**AST + BM25/embedding hybrid (chosen approach)**

The three strategies cover different failure modes. Tree-sitter provides chunk quality. BM25 covers exact-match queries. Embeddings cover semantic queries. Reciprocal rank fusion combines signals at query time. If the embedding layer is impractical for a consumer project, AST + BM25 alone is the recommended degraded mode.

**Index update strategies**

Rebuild on merge to main always reflects main but pays full parse-and-embed cost on every PR. For large codebases with frequent merges, this becomes a CI bottleneck.

Incremental updates re-index only changed files. A one-file change is cheap. A cross-cutting refactor is not: without a dependency graph, transitive invalidations go undetected and the index drifts.

On-demand agent-triggered rebuilds compare a file-hash manifest against the working tree and re-index dirty files at query time. This suits active development but adds latency and requires write access to the index store.

Cold-start cost applies before any update strategy: tree-sitter over all source files (seconds), embedding generation for all chunks (minutes, rate-limited), and persisting both the BM25 inverted index and vector store. Starting with AST + BM25 only defers the embedding cost until the simpler pipeline is validated.

---

## Consequences

**Pros**

- Agents retrieve function- or class-level context without loading whole files, reducing context window pressure.
- Retrieval is agent-initiated and on-demand, consistent with the harness's lazy-load model.
- BM25 covers exact symbol lookup; embeddings cover semantic queries. The hybrid needs one retrieval pass.
- Tree-sitter has grammars for C#, TypeScript, Python, and Lua.

**Cons**

- A stale index produces retrieval misses. A miss that falls back to full-file loading costs more tokens than no subsystem.
- Tree-sitter is a native dependency. Consumer projects must have it available.
- The embedding pipeline requires a vector store and embedding model, neither of which the harness currently provides.
- Cold-start build time scales with codebase size and is bottlenecked by embedding generation.
- Incremental updates are unsafe for cross-cutting refactors without a dependency graph.
- The update trigger strategy must be chosen per consumer project. The wrong choice either wastes CI resources or allows the index to drift.

**Technical debt**

Retrieval miss fallback behavior must be defined before the subsystem is stable. The index update strategy is unresolved and must be settled before any consumer project uses this in production.

---

## Enforcement / Guidance

- Consumer projects opt in via an explicit configuration file (schema TBD). Agents must not attempt retrieval without it.
- A skill (tentatively `code-retrieval`) gates all agent access to the subsystem, following the pattern of `adr-creation` and `continuous-learning`. Direct index queries outside the skill are not permitted.
- The subsystem must warn when the index is stale relative to the working tree. Silent misses are not acceptable.
- Retrieval miss behavior must be explicit in the skill or configuration: fail loudly, or fall back to full-file loading with a logged warning.
- This ADR must be updated to `Active` and technology choices finalized before the subsystem leaves prototype.

---

## References

- Robertson, S. and Zaragoza, H., "The Probabilistic Relevance Framework: BM25 and Beyond", Foundations and Trends in Information Retrieval, 2009
- Tree-sitter project: https://tree-sitter.github.io/tree-sitter/
- LlamaIndex CodeSplitter documentation: https://docs.llamaindex.ai
- Aider repo-map design: https://aider.chat/docs/repomap.html
