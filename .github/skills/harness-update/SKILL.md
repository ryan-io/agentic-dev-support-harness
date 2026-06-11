---
name: harness-update
description: >
  Pull harness improvements from the template repository into an adopted project.
  Reads the committed version anchor, previews overwrites and merges, applies them
  through the update engine, and lands one revertable commit. Use when the user wants
  to "update the harness", "pull template changes", "sync from the template", or asks
  whether the harness is out of date.
---

# Harness Update Skill

Pull-based update for downstream projects. The engine is `.github/scripts/update.py`;
the file classification lives in `.github/scripts/update-manifest.json`. Decision
record: `docs/adr/adr-setup-add-harness-update-mechanism.md`.

## Preconditions

1. This is a downstream project, not the template source. The engine refuses when
   `.github/TEMPLATE_SOURCE` is present; do not work around the guard.
2. The anchor `.github/harness-version.json` exists and parses. If it is missing
   (project adopted before the update mechanism existed), run the one-time bootstrap:
   ask the developer for the adopted harness commit (or nearest approximation) and
   the harness source URL, then run
   `python .github/scripts/update.py --anchor <sha> --source <url>` and commit the
   anchor. An approximate anchor means the first update may surface extra conflicts;
   say so. If `update.py` itself is missing too, the whole mechanism predates this
   project: run `python .github/scripts/bootstrap-update.py --target <path>` from a
   harness clone, which installs the engine, manifest, and both lifecycle skills and
   writes the anchor in one pass.
3. The working tree is clean. The update lands as a single revertable commit; ask the
   developer to commit or stash first if `git status` shows changes.

## Workflow

### Step 1: Check update state

Run `python .github/scripts/update.py --check`. It reports the anchored commit, the
harness target commit, and how many commits and files behind the project is. If
already current, stop and say so. (`--source <url>` overrides the anchored source;
`--to <ref>` targets a specific harness ref instead of HEAD.)

### Step 2: Surface the preview

Run `python .github/scripts/update.py --dry-run` and show the developer the full
output: every overwrite-set file that changed, every merge-set file with whether it
merges cleanly or will conflict, and every skipped path (excluded, out of scope, or
locally removed; locally deleted files are never resurrected). Nothing has changed
yet.

### Step 3: Apply

Only after explicit confirmation of the previewed plan, run
`python .github/scripts/update.py --run`. The engine re-enforces the guards, applies
the overwrite set, three-way merges the merge set (base: anchored harness version,
ours: project file, theirs: new harness version), reruns `sync-claude-rules.py`,
runs `validate-system.py`, bumps the anchor, and commits. A non-zero gate result
rolls back; nothing partial lands.

### Step 4: Resolve conflicts, if any

If the merge set produced conflict markers, the engine stops before the commit (exit
code 2) and lists the conflicted files. Walk the developer through each conflict:
show both sides, explain what the harness changed and what the project customized,
and apply the developer's resolution. Never auto-resolve instruction-file conflicts.
Then run `python .github/scripts/update.py --finish`, which verifies no markers
remain, runs the gate, bumps the anchor, and commits.

### Step 5: Verify and hand back

Confirm the engine reported the update commit and `validate-system.py` is green.
Tell the developer the reversal path: one `git revert` of the update commit restores
the pre-update tree, anchor included. Summarize what changed in one or two sentences,
pointing at the commit rather than restating the diff.

## Revising a prior update

To redo or adjust an update: revert the update commit (this also restores the
previous anchor), make the change (for example, resolve a conflict differently), and
run the skill again from the check step. Applying the same target twice is a no-op:
the engine reports "up to date" once the anchor matches.
