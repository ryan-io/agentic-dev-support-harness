#!/usr/bin/env python3
"""
update.py
The harness-update engine. Pulls harness improvements from the template
repository into an adopted project as one revertable commit.

Mechanism: a committed anchor (.github/harness-version.json) records the
harness source and the last-applied commit. The engine clones the source,
diffs anchor..target, and applies each changed file per the manifest
(.github/scripts/update-manifest.json): the overwrite set is applied
directly, the merge set goes through a three-way merge (git merge-file)
with the anchored version as base, and excluded or out-of-scope paths are
skipped. Files the project deleted locally are never resurrected. Merge
conflicts stop the run before the commit; resolve them, then --finish.

Stdlib only. Fails clean: a bad manifest raises ManifestError, a failed
run rolls back the working tree before raising. Run from the repo root:
  python .github/scripts/update.py --check                 # anchor state vs source, read-only
  python .github/scripts/update.py --dry-run               # preview the run, no changes
  python .github/scripts/update.py --run                   # apply, gate, commit
  python .github/scripts/update.py --finish                # complete a conflicted run
  python .github/scripts/update.py --anchor <sha> --source <url>  # one-time bootstrap
Optional on check/dry-run/run: --source <url> overrides the anchored source,
--to <ref> targets a specific harness ref instead of the source HEAD.

Decision record: docs/adr/adr-setup-add-harness-update-mechanism.md
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

MANIFEST_PATH = os.path.join(".github", "scripts", "update-manifest.json")
ANCHOR_PATH = os.path.join(".github", "harness-version.json")
SYNC_SCRIPT = os.path.join(".github", "scripts", "sync-claude-rules.py")
VALIDATE_SCRIPT = os.path.join(".github", "scripts", "validate-system.py")
PENDING_PATH = os.path.join(".git", "harness-update-pending.json")
CONFLICT_MARKER = "<<<<<<<"


class ManifestError(Exception):
    """Raised when the manifest or anchor is malformed or missing."""


class UpdateError(Exception):
    """Raised when a run step fails; the run rolls back before raising."""


# --- Manifest and classification --------------------------------------------

def _norm(p):
    return p.replace("\\", "/").strip()


def load_manifest(path=MANIFEST_PATH):
    """Load and parse the manifest. Raises ManifestError on read/parse failure."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise ManifestError(f"manifest not found: {path}")
    except json.JSONDecodeError as exc:
        raise ManifestError(f"manifest is not valid JSON: {exc}")
    for key in ("governance_roots", "merge_set", "exclude", "guards"):
        if key not in data:
            raise ManifestError(f"manifest missing '{key}'")
    return data


def _under(path, root):
    """True when path equals a file root or sits under a directory root."""
    p = _norm(path).rstrip("/")
    r = _norm(root)
    if r.endswith("/"):
        base = r.rstrip("/")
        return p == base or p.startswith(base + "/")
    return p == r


def classify(path, manifest):
    """Sort one upstream path into merge | excluded | overwrite | out-of-scope."""
    p = _norm(path)
    if any(_under(p, m) for m in manifest.get("merge_set", [])):
        return "merge"
    if any(_under(p, e) for e in manifest.get("exclude", [])):
        return "excluded"
    if any(_under(p, o) for o in manifest.get("out_of_scope", [])):
        return "out-of-scope"
    if any(_under(p, r) for r in manifest.get("governance_roots", [])):
        return "overwrite"
    return "out-of-scope"


# --- Anchor ------------------------------------------------------------------

def read_anchor(path=ANCHOR_PATH):
    """Read the committed anchor. Raises ManifestError when absent or malformed."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise ManifestError(
            f"anchor not found: {path}. This project predates the update "
            "mechanism; bootstrap with --anchor <sha> --source <url>.")
    except json.JSONDecodeError as exc:
        raise ManifestError(f"anchor is not valid JSON: {exc}")
    if not data.get("commit") or not data.get("source"):
        raise ManifestError(f"anchor missing 'source' or 'commit': {path}")
    return data


def write_anchor(source, commit, path=ANCHOR_PATH):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"source": source, "commit": commit}, fh, indent=2)
        fh.write("\n")


# --- Git plumbing ------------------------------------------------------------

def _git(args, cwd=None, check=True):
    res = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd)
    if check and res.returncode != 0:
        raise UpdateError(f"git {' '.join(args)} failed: {res.stderr.strip()}")
    return res


def working_tree_clean():
    return _git(["status", "--porcelain"]).stdout.strip() == ""


def clone_source(source):
    """Clone the harness source (URL or local path) into a temp dir."""
    tmp = tempfile.mkdtemp(prefix="harness-update-")
    res = _git(["clone", "--quiet", source, tmp], check=False)
    if res.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        raise UpdateError(f"cannot clone harness source '{source}': "
                          f"{res.stderr.strip()}")
    return tmp


def resolve_target(tmp, ref=None):
    """Resolve the target commit in the clone (HEAD unless --to was given)."""
    res = _git(["rev-parse", ref or "HEAD"], cwd=tmp, check=False)
    if res.returncode != 0:
        raise UpdateError(f"cannot resolve target ref '{ref or 'HEAD'}': "
                          f"{res.stderr.strip()}")
    return res.stdout.strip()


def upstream_diff(tmp, base, target):
    """List of (status, path) changed in the harness between base and target."""
    res = _git(["diff", "--name-status", "--no-renames", base, target], cwd=tmp,
               check=False)
    if res.returncode != 0:
        raise UpdateError(
            f"cannot diff {base[:9]}..{target[:9]} in the source clone "
            f"(is the anchor commit real?): {res.stderr.strip()}")
    changes = []
    for line in res.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0][0]
        if status == "T":  # type change: treat as modification
            status = "M"
        changes.append((status, _norm(parts[1])))
    return changes


def show_file(tmp, commit, path):
    """File content at a commit in the clone, or None when absent there."""
    res = _git(["show", f"{commit}:{path}"], cwd=tmp, check=False)
    return res.stdout if res.returncode == 0 else None


# --- Planning ----------------------------------------------------------------

def _read_local(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except (FileNotFoundError, IsADirectoryError):
        return None


def build_plan(manifest, tmp, base, target):
    """
    Turn the upstream diff into per-file actions. Each action:
    {path, set, status, op, note}. op is one of: write, merge, delete, skip.
    """
    plan = []
    for status, path in upstream_diff(tmp, base, target):
        bucket = classify(path, manifest)
        if bucket in ("excluded", "out-of-scope"):
            plan.append({"path": path, "set": bucket, "status": status,
                         "op": "skip", "note": bucket})
            continue
        local = _read_local(path)
        old = show_file(tmp, base, path)
        new = show_file(tmp, target, path)
        if bucket == "overwrite":
            plan.append(_plan_overwrite(path, status, local, old, new))
        else:
            plan.append(_plan_merge(path, status, local, old, new))
    return plan


def _plan_overwrite(path, status, local, old, new):
    a = {"path": path, "set": "overwrite", "status": status}
    if status == "D":
        if local is None:
            a.update(op="skip", note="already absent")
        elif local == old:
            a.update(op="delete", note="upstream deleted")
        else:
            a.update(op="skip", note="upstream deleted but local modified; left in place")
    elif status == "A":
        if local == new:
            a.update(op="skip", note="already current")
        elif local is None:
            a.update(op="write", note="new upstream file", content=new)
        else:
            a.update(op="write", note="replaced unexpected local file", content=new)
    else:  # M
        if local is None:
            a.update(op="skip", note="locally removed; not resurrected")
        elif local == new:
            a.update(op="skip", note="already current")
        elif local == old:
            a.update(op="write", note="upstream modified", content=new)
        else:
            a.update(op="write", note="local edits replaced (consume-only file)",
                     content=new)
    return a


def _plan_merge(path, status, local, old, new):
    a = {"path": path, "set": "merge", "status": status}
    if status == "D":
        a.update(op="skip", note="upstream deleted; kept local (project owns this file)")
    elif local is None:
        if status == "A":
            a.update(op="write", note="new upstream file", content=new)
        else:
            a.update(op="skip", note="locally removed; not resurrected")
    elif local == new:
        a.update(op="skip", note="already current")
    else:
        a.update(op="merge", note="three-way merge", base=old or "", theirs=new or "")
    return a


# --- Applying ----------------------------------------------------------------

def _write_file(path, content):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def merge_three_way(path, base_text, theirs_text, base_label, theirs_label):
    """
    git merge-file on temp copies; writes the merged result (conflict markers
    included) back to path. Returns the conflict count (0 = clean).
    """
    tdir = tempfile.mkdtemp(prefix="merge3-")
    try:
        ours_f = os.path.join(tdir, "ours")
        base_f = os.path.join(tdir, "base")
        theirs_f = os.path.join(tdir, "theirs")
        shutil.copyfile(path, ours_f)
        _write_file(base_f, base_text)
        _write_file(theirs_f, theirs_text)
        res = subprocess.run(
            ["git", "merge-file", "-L", "project", "-L", base_label,
             "-L", theirs_label, ours_f, base_f, theirs_f],
            capture_output=True, text=True)
        if res.returncode < 0:
            raise UpdateError(f"git merge-file errored on {path}: "
                              f"{res.stderr.strip()}")
        shutil.copyfile(ours_f, path)
        return res.returncode
    finally:
        shutil.rmtree(tdir, ignore_errors=True)


def apply_plan(plan, base, target, dry_run):
    """
    Perform (or preview) the plan. Returns (report_lines, conflicts, created):
    conflicts is the list of conflicted paths, created the paths this run
    wrote that did not exist before (for rollback).
    """
    lines, conflicts, created = [], [], []
    prefix = "[dry-run] would" if dry_run else "did"
    for a in sorted(plan, key=lambda x: (x["set"], x["path"])):
        path, op = a["path"], a["op"]
        if op == "skip":
            lines.append(f"  skip   [{a['set']:11}] {path} -- {a['note']}")
            continue
        if op == "delete":
            if not dry_run:
                os.remove(path)
            lines.append(f"  {prefix} delete [{a['set']}] {path}")
            continue
        if op == "write":
            if not dry_run:
                if not os.path.exists(path):
                    created.append(path)
                _write_file(path, a["content"])
            lines.append(f"  {prefix} write  [{a['set']}] {path} -- {a['note']}")
            continue
        # op == "merge"
        if dry_run:
            # Probe the merge on a throwaway copy to predict conflicts.
            probe = tempfile.mkdtemp(prefix="probe3-")
            try:
                copy = os.path.join(probe, "ours")
                shutil.copyfile(path, copy)
                n = merge_three_way(copy, a["base"], a["theirs"],
                                    f"harness {base[:9]}", f"harness {target[:9]}")
            finally:
                shutil.rmtree(probe, ignore_errors=True)
            verdict = "clean" if n == 0 else f"{n} CONFLICT(s)"
            lines.append(f"  [dry-run] would merge  [merge] {path} -- {verdict}")
            if n:
                conflicts.append(path)
        else:
            n = merge_three_way(path, a["base"], a["theirs"],
                                f"harness {base[:9]}", f"harness {target[:9]}")
            verdict = "clean" if n == 0 else f"{n} CONFLICT(s) -- markers left in file"
            lines.append(f"  {prefix} merge  [merge] {path} -- {verdict}")
            if n:
                conflicts.append(path)
    return lines, conflicts, created


# --- Gate, commit, rollback ----------------------------------------------------

def _closing_gate():
    """Run sync then validate. Raises UpdateError on a non-zero result."""
    for script in (SYNC_SCRIPT, VALIDATE_SCRIPT):
        if not os.path.isfile(script):
            print(f"  WARNING: {script} not found; gate step skipped")
            continue
        print(f"  running {script} ...")
        res = subprocess.run([sys.executable, script],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode != 0:
            raise UpdateError(f"closing gate failed: {script} exited {res.returncode}")


def _rollback(created):
    """Restore the pre-update tree: reset tracked files, remove created ones."""
    _git(["reset", "--hard"], check=False)
    for path in created:
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass


def _commit(target):
    _git(["add", "-A"])
    _git(["commit", "-m", f"chore: update harness to {target[:9]}"])
    sha = _git(["rev-parse", "--short", "HEAD"]).stdout.strip()
    print(f"\nUpdate complete: commit {sha}.")
    print(f"Reversal: git revert {sha} restores the pre-update tree, anchor included.")


# --- Guards --------------------------------------------------------------------

def refuse_if_source(manifest):
    sentinel = manifest.get("guards", {}).get("refuse_if_present",
                                              ".github/TEMPLATE_SOURCE")
    if os.path.exists(sentinel):
        print(f"REFUSED: upstream sentinel present ({sentinel}); "
              "this looks like the template source, which has nothing to pull.")
        return True
    return False


# --- Commands --------------------------------------------------------------------

def cmd_check(manifest, source_override=None, to_ref=None):
    anchor = read_anchor()
    source = source_override or anchor["source"]
    print(f"Anchor: {anchor['commit'][:9]} from {source}")
    tmp = clone_source(source)
    try:
        target = resolve_target(tmp, to_ref)
        if target == anchor["commit"]:
            print("Up to date: anchor matches the harness target commit.")
            return 0
        res = _git(["rev-list", "--count",
                    f"{anchor['commit']}..{target}"], cwd=tmp, check=False)
        behind = res.stdout.strip() if res.returncode == 0 else "?"
        changed = len(upstream_diff(tmp, anchor["commit"], target))
        print(f"Behind: {behind} commit(s); target {target[:9]}; "
              f"{changed} file(s) differ. Run --dry-run for the plan.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cmd_execute(manifest, dry_run, source_override=None, to_ref=None):
    anchor = read_anchor()
    source = source_override or anchor["source"]
    if not dry_run and not working_tree_clean():
        print("REFUSED: working tree is dirty. Commit or stash first; "
              "the update must land as a single revertable commit.")
        return 1
    tmp = clone_source(source)
    try:
        target = resolve_target(tmp, to_ref)
        base = anchor["commit"]
        if target == base:
            print("Up to date: nothing to apply.")
            return 0
        mode = "DRY RUN (no changes)" if dry_run else "LIVE RUN"
        print(f"harness-update {mode}: {base[:9]} -> {target[:9]}\n")
        plan = build_plan(manifest, tmp, base, target)
        if not plan:
            print("Upstream changed, but no classified file differs. "
                  "Bumping the anchor only." if not dry_run else
                  "Upstream changed, but no classified file differs.")
            if not dry_run:
                write_anchor(source, target)
                _commit(target)
            return 0
        try:
            lines, conflicts, created = apply_plan(plan, base, target, dry_run)
        except UpdateError:
            if not dry_run:
                _rollback([])
            raise
        for ln in lines:
            print(ln)
        if dry_run:
            n = len(conflicts)
            print(f"\nDry run complete. No changes were made."
                  + (f" Expect {n} conflicted file(s)." if n else ""))
            return 0
        if conflicts:
            # Record the conflicted paths so --finish gates on exactly
            # these files, not the whole merge set (B7): a merge-set doc
            # that legitimately contains conflict-marker text must not
            # block completion.
            with open(PENDING_PATH, "w", encoding="utf-8") as fh:
                json.dump({"source": source, "target": target,
                           "conflicts": conflicts}, fh)
            print("\nCONFLICTS: the run stopped before the commit. Resolve the "
                  "markers in:")
            for c in conflicts:
                print(f"  - {c}")
            print("then run: python .github/scripts/update.py --finish")
            return 2
        try:
            write_anchor(source, target)
            print("\nClosing gate (sync, then validate):")
            _closing_gate()
        except UpdateError as exc:
            print(f"\nERROR: {exc}\nRolling back ...")
            _rollback(created)
            return 1
        _commit(target)
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cmd_finish(manifest):
    """Complete a run that stopped on conflicts: gate, anchor, commit."""
    try:
        with open(PENDING_PATH, "r", encoding="utf-8") as fh:
            pending = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        print("REFUSED: no pending conflicted update "
              f"({PENDING_PATH} absent). Run --run first.")
        return 1
    # Gate only the paths the run actually conflicted on (B7). A pending
    # file from before this fix carries no conflict list; fall back to the
    # whole merge set rather than skipping the gate.
    recorded = pending.get("conflicts")
    if isinstance(recorded, list):
        candidates = [p for p in recorded if isinstance(p, str)]
    else:
        candidates = manifest.get("merge_set", [])
    unresolved = [p for p in candidates
                  if os.path.isfile(p) and CONFLICT_MARKER in _read_local(p)]
    if unresolved:
        print("REFUSED: conflict markers remain in:")
        for p in unresolved:
            print(f"  - {p}")
        return 1
    try:
        write_anchor(pending["source"], pending["target"])
        print("Closing gate (sync, then validate):")
        _closing_gate()
    except UpdateError as exc:
        # No rollback: the developer's conflict resolutions stay in place.
        print(f"ERROR: {exc}\nFix the failure and run --finish again.")
        return 1
    _commit(pending["target"])
    os.remove(PENDING_PATH)
    return 0


def cmd_anchor(manifest, sha, source_override):
    """One-time bootstrap for projects adopted before the update mechanism."""
    try:
        anchor = read_anchor()
        source = source_override or anchor["source"]
    except ManifestError:
        source = source_override
    if not source:
        print("REFUSED: --anchor on a project with no anchor needs --source <url>.")
        return 1
    tmp = clone_source(source)
    try:
        resolved = resolve_target(tmp, sha)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    write_anchor(source, resolved)
    print(f"Anchor written: {resolved[:9]} from {source}")
    print("Commit it; an approximate anchor can surface extra conflicts on "
          "the first update.")
    return 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    args = list(argv)

    def take_value(flag):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                print(f"{flag} needs a value", file=sys.stderr)
                sys.exit(1)
            val = args[i + 1]
            del args[i:i + 2]
            return val
        return None

    source = take_value("--source")
    to_ref = take_value("--to")
    anchor_sha = take_value("--anchor")
    cmd = args[0] if args else None
    if anchor_sha is not None and cmd is not None:
        print("--anchor cannot be combined with another command", file=sys.stderr)
        return 1
    if anchor_sha is None and cmd is None:
        print("Expected one of: --check, --dry-run, --run, --finish, "
              "--anchor <sha> [--source <url>]", file=sys.stderr)
        return 1
    try:
        manifest = load_manifest()
        if refuse_if_source(manifest):
            return 1
        if anchor_sha is not None:
            return cmd_anchor(manifest, anchor_sha, source)
        if cmd == "--check":
            return cmd_check(manifest, source, to_ref)
        if cmd == "--dry-run":
            return cmd_execute(manifest, dry_run=True,
                               source_override=source, to_ref=to_ref)
        if cmd == "--run":
            return cmd_execute(manifest, dry_run=False,
                               source_override=source, to_ref=to_ref)
        if cmd == "--finish":
            return cmd_finish(manifest)
    except (ManifestError, UpdateError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Unknown argument: {cmd} (try --help)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
