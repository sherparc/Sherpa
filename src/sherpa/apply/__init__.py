"""``sherpa apply`` — the approved plan → files under ``.claude/`` plus ``.sherpa/state.json`` (ADR-0008, ADR-0013).

Two phases, tested separately: ``plan_files()`` is pure — (targets, current files, state) → one ``Action`` per
file with ``+ new``, ``~ updated``, ``= unchanged`` or ``! skipped`` and the exact bytes to write; ``write()``
writes them, runs the checker and rolls back when the write introduced a FAIL. Dry run is the default.

Ownership (ADR-0013) under one rule (ADR-0016): **sherpa never overwrites what exists in the user's repo — it
only adds**, and rewrites nothing but bytes it wrote itself and that nobody changed since (hash in the state).
A *managed* file is sherpa's as a whole — a hash mismatch means a hand edit and the file is skipped. A *blocks*
file is seeded once; afterwards only the marked blocks are sherpa's, each with its own hash, and a hand-edited
block is skipped on its own. ``.claude/settings.json`` gets sherpa's hook entries merged in; everything else in
it stays. A file that exists without a state record is never touched (``sherpa adopt``), except that root and
nested ``CLAUDE.md``/``AGENTS.md`` get sherpa's block appended; a file the state records as ``adopted`` is never
touched either (ADR-0007).

Removal (ADR-0048, the ``- destroy`` half of the Terraform model): a state record whose file the plan no longer
renders — a rejected entry, a unit gone from the trunk — is taken back when the bytes are still sherpa's: a
managed file whose hash equals the state is deleted, a marked block whose hash equals the state is cut out of its
file (the file goes too when nothing but sherpa's blocks was in it), sherpa's hook groups leave ``settings.json``.
A hand-edited file or block stays and its record is dropped — ``yours now``. ``apply --remove`` does the same
for every generated record at once, base files included: the uninstall. Nothing adopted is ever removed.

Determinism: same plan, model and files → same actions, same bytes; the second run is all ``=``.

The bytes ``write()`` puts down were computed from the preview's read; a file that changed in between (an editor,
a second agent) is skipped with ``changed since the preview`` instead of overwritten (ADR-0030). A path with a
symlink in it is never written through (ADR-0031): the bytes would land in a file that is not the target. Every
file is written whole or not at all (``sherpa.atomic``), and an ``OSError`` half-way rolls the written files back
like a new checker FAIL does (ADR-0032).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from sherpa import __version__, atomic
from sherpa.apply import state as state_mod
from sherpa.apply.render import HOOK_COMMAND, Renderer, Target, selected
from sherpa.apply.state import ADOPTED, BLOCKS, GENERATED, JSON_HOOKS, MANAGED, FileRecord, State
from sherpa.check import Finding, block_contents, content_hash
from sherpa.config import TARGETS
from sherpa.model import Model
from sherpa.plan import Plan

NEW, UPDATED, UNCHANGED, SKIPPED, REMOVED = "+", "~", "=", "!", "-"


@dataclass(frozen=True)
class Action:
    target: Target
    op: str  # + ~ = ! -
    detail: str  # human line: "new", "block facts updated", "hand-edited (skipped)", "removed (…)", …
    new: str | None  # bytes to write; None when nothing is written
    old: str | None  # current content for rollback; None = file did not exist
    record: FileRecord | None  # state after this action; None = keep the previous record (or drop it, see forget)
    delete: bool = False  # remove the file instead of writing it (ADR-0048); ``old`` restores it on rollback
    forget: bool = False  # drop the state record — the file is gone or yours now
    crlf: bool = False  # the file on disk had CRLF line endings when it was written or removed — a rollback keeps them

    @property
    def path(self) -> str:
        return self.target.path


@dataclass
class Result:
    actions: list[Action]
    state: State
    findings: list[Finding] = field(default_factory=list)  # checker output after the write
    rolled_back: bool = False
    written: int = 0
    removed: int = 0  # files deleted (ADR-0048)
    error: str | None = None  # the OSError that stopped the write (ADR-0032)
    left: list[str] = field(default_factory=list)  # files the rollback could not restore

    def counts(self) -> dict[str, int]:
        return {op: sum(a.op == op for a in self.actions) for op in (NEW, UPDATED, UNCHANGED, SKIPPED, REMOVED)}


class StalePlan(ValueError):
    pass


# ---------------------------------------------------------------- phase 1: pure


def targets_for(
    plan: Plan,
    model: Model,
    version: str = __version__,
    *,
    home: str = ".agents",
    targets: tuple[str, ...] = TARGETS,
    everything: bool = False,
) -> list[Target]:
    if plan.model.get("rev") != model.git.trunk.rev:
        raise StalePlan(
            f"harness-plan.yaml was made from {plan.model.get('rev', '?')[:10]}, the model is at "
            f"{model.git.trunk.rev[:10]} — run `sherpa plan` first"
        )
    if any(e.kind == "outcome" and e.decision == "reject" for e in plan.entries):
        raise ValueError("the outcome entry is rejected — a harness without a signal is not created (ADR-0008)")
    if everything:  # every entry as if accepted and uncovered: what sherpa *would* render — adopt uses it to
        # recognise its own rendering of an entry that is no longer selected (ADR-0048, F25)
        from dataclasses import replace

        plan = replace(plan, entries=[replace(e, decision="accept", covered=None) for e in plan.entries])
    return Renderer(plan, model, version, home=home, targets=targets).targets()


def plan_files(targets: list[Target], repo: Path, state: State, *, remove_all: bool = False) -> list[Action]:
    """One action per rendered target, then one per generated record the targets no longer cover (ADR-0048):
    entry-bound files whose entry left the plan; with ``remove_all`` every generated record, base files too."""
    actions = [_plan_one(t, _read(repo / t.path), state.files.get(t.path), repo) for t in targets]
    rendered = {t.path for t in targets}
    for path, rec in sorted(state.files.items()):
        if path in rendered or rec.origin != GENERATED or (rec.entry is None and not remove_all):
            continue
        actions.append(_plan_removal(path, rec, _read(repo / path), repo, "all" if remove_all else "plan"))
    return actions


def _plan_removal(path: str, rec: FileRecord, current: str | None, repo: Path, why: str) -> Action:
    """Take back sherpa's own unchanged bytes; leave everything else and drop the record (``yours now``)."""
    t = Target(path, rec.mode, rec.entry)
    reason = "no longer in the plan" if why == "plan" else "--remove"
    if current is None:
        return Action(t, REMOVED, "already gone — record dropped", None, None, None, forget=True)
    if _through_symlink(repo, path):
        return Action(t, SKIPPED, THROUGH_SYMLINK, None, current, None)
    if rec.mode == MANAGED:
        if content_hash(current) != rec.hash:
            return Action(t, SKIPPED, "hand-edited — yours now (kept)", None, current, None, forget=True)
        return Action(t, REMOVED, f"removed ({reason})", None, current, None, delete=True, forget=True)
    if rec.mode == JSON_HOOKS:
        return _plan_hooks_removal(t, current, reason)
    return _plan_blocks_removal(t, rec, current, reason)


def _plan_blocks_removal(t: Target, rec: FileRecord, current: str, reason: str) -> Action:
    if rec.hash is not None and content_hash(current) == rec.hash:  # seeded by sherpa, untouched since
        return Action(t, REMOVED, f"removed ({reason})", None, current, None, delete=True, forget=True)
    try:
        have = block_contents(current)
    except ValueError as e:
        return Action(t, SKIPPED, f"markers broken: {e} (skipped)", None, current, None)
    cut = [n for n, h in rec.blocks.items() if n in have and content_hash(have[n]) == h]
    kept = [n for n in rec.blocks if n in have and n not in cut]
    if not cut:
        detail = "block " + ", ".join(kept) + " hand-edited — yours now (kept)" if kept else "no sherpa block left"
        return Action(t, SKIPPED, detail, None, current, None, forget=True)
    rest = _cut_blocks(current, set(cut))
    if not rest.strip():  # nothing but sherpa's blocks was in the file: it was sherpa's whole
        return Action(t, REMOVED, f"removed ({reason})", None, current, None, delete=True, forget=True)
    detail = "block " + ", ".join(cut) + f" removed ({reason})"
    if kept:
        detail += "; block " + ", ".join(kept) + " hand-edited — yours now"
    return Action(t, REMOVED, detail, rest, current, None, forget=True)


def _cut_blocks(text: str, names: set[str]) -> str:
    """Drop the named blocks, markers included, and the one blank line ``apply`` put before an appended block."""
    from sherpa.check import MARKER

    out: list[str] = []
    skip = False
    for line in text.split("\n"):
        m = MARKER.match(line)
        if m and m.group(1) == "begin" and m.group(2) in names:
            skip = True
            if out and out[-1] == "":
                out.pop()
            continue
        if m and m.group(1) == "end" and skip:
            skip = False
            continue
        if not skip:
            out.append(line)
    return "\n".join(out)


def _plan_hooks_removal(t: Target, current: str, reason: str) -> Action:
    """Sherpa's hook groups are the ones that call ``sherpa-outcome.py`` — identified, not hashed: another key
    edited by hand does not keep sherpa's groups in the file."""
    try:
        data = json.loads(current)
        if not isinstance(data, dict):
            raise ValueError("top level is not an object")
    except ValueError as e:
        return Action(t, SKIPPED, f"not valid JSON: {e} (skipped)", None, current, None)
    hooks = data.get("hooks") if isinstance(data.get("hooks"), dict) else {}
    removed = []
    for event, groups in list(hooks.items()):
        if not isinstance(groups, list):
            continue
        rest = [g for g in groups if not (isinstance(g, dict) and _has_sherpa_hook(g))]
        if len(rest) != len(groups):
            removed.append(event)
        if rest:
            hooks[event] = rest
        else:
            del hooks[event]
    if not removed:
        return Action(t, SKIPPED, "no sherpa hook in it — yours now (kept)", None, current, None, forget=True)
    if not hooks:
        data.pop("hooks", None)
    if not data:  # sherpa created the file for its hooks alone
        return Action(t, REMOVED, f"removed ({reason})", None, current, None, delete=True, forget=True)
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    detail = "hooks removed: " + ", ".join(removed) + f" ({reason})"
    return Action(t, REMOVED, detail, content, current, None, forget=True)


THROUGH_SYMLINK = "symlink in the path — never written through (skipped)"


def _through_symlink(repo: Path, rel: str) -> bool:
    """True when any component of ``rel`` below the repo root is a symlink (ADR-0031): the bytes would land in
    another file — outside the repository, or inside it under a second record — so the path is not written to."""
    p = repo
    for part in rel.split("/"):
        p = p / part
        if p.is_symlink():
            return True
    return False


def _read(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def _uses_crlf(path: Path) -> bool:
    """A file that has CRLF line endings on disk keeps them (ADR-0016: sherpa rewrites only its own bytes — the
    line endings of a file it appends to or cuts from are the user's). Read as bytes: text mode would hide it."""
    try:
        return b"\r\n" in path.read_bytes()
    except OSError:
        return False


def _put(path: Path, text: str, crlf: bool) -> None:
    atomic.write_text(path, text.replace("\n", "\r\n") if crlf else text)


def _plan_one(t: Target, current: str | None, rec: FileRecord | None, repo: Path) -> Action:
    if _through_symlink(repo, t.path):
        return Action(t, SKIPPED, THROUGH_SYMLINK, None, current, None)
    if rec is not None and rec.origin == ADOPTED:
        if current is None:
            return Action(t, SKIPPED, "adopted file is gone — `sherpa adopt` drops the record", None, None, None)
        return Action(t, SKIPPED, "adopted — yours, never touched (skipped)", None, current, None)
    if t.mode == MANAGED:
        return _plan_managed(t, current, rec)
    if t.mode == JSON_HOOKS:
        return _plan_hooks(t, current, rec)
    return _plan_blocks(t, current, rec)


def _plan_managed(t: Target, current: str | None, rec: FileRecord | None) -> Action:
    new_rec = FileRecord(MANAGED, entry=t.entry, hash=content_hash(t.content))
    if current is None:
        return Action(t, NEW, "new", t.content, None, new_rec)
    if rec is None:
        return Action(t, SKIPPED, "exists, not managed by sherpa — `sherpa adopt` takes it over", None, current, None)
    if content_hash(current) != rec.hash:
        return Action(t, SKIPPED, "hand-edited (skipped)", None, current, None)
    if current == t.content:
        return Action(t, UNCHANGED, "unchanged", None, current, new_rec)
    return Action(t, UPDATED, "updated", t.content, current, new_rec)


def _plan_blocks(t: Target, current: str | None, rec: FileRecord | None) -> Action:
    hashes = {n: content_hash(v) for n, v in t.blocks.items()}
    if current is None:  # seeded whole: the hash says so until a hand touches anything (ADR-0048)
        rec_new = FileRecord(BLOCKS, entry=t.entry, hash=content_hash(t.content), blocks=hashes)
        return Action(t, NEW, "new", t.content, None, rec_new)
    try:
        have = block_contents(current)
    except ValueError as e:
        return Action(t, SKIPPED, f"markers broken: {e} (skipped)", None, current, None)
    if rec is None:
        # Never overwrite what exists (ADR-0016): without a state record every block in the file is somebody's.
        if have:
            return Action(
                t, SKIPPED, "exists with sherpa markers but no state record — `sherpa adopt`", None, current, None
            )
        if not t.append:
            return Action(
                t, SKIPPED, "exists, not managed by sherpa — `sherpa adopt` takes it over", None, current, None
            )
        body = current if current.endswith("\n") else current + "\n"
        merged = body + "\n" + "\n".join(_marked(t, n) for n in t.blocks) + "\n"
        return Action(
            t,
            UPDATED,
            "block " + ", ".join(t.blocks) + " appended",
            merged,
            current,
            FileRecord(BLOCKS, entry=t.entry, blocks=hashes),
        )
    updated, skipped, kept = [], [], dict(rec.blocks)
    replace: dict[str, str] = {}
    for name, inner in t.blocks.items():
        if name not in have:
            skipped.append(f"block {name} removed by hand")
            kept.pop(name, None)
            continue
        known = rec.blocks.get(name)
        if known is None:
            skipped.append(f"block {name} not written by sherpa")  # same name, somebody else's block: add-only
            continue
        if content_hash(have[name]) != known:
            skipped.append(f"block {name} hand-edited")
            continue
        kept[name] = hashes[name]
        if have[name] != inner:
            updated.append(name)
            replace[name] = inner
    # Still sherpa's seed plus its blocks: the hash from the state says so, or — for a record older than the
    # hash (before ADR-0048) — the file equals the rendering byte for byte.
    whole = (rec.hash is not None and content_hash(current) == rec.hash) or current == t.content
    if updated:
        merged = _replace_blocks(current, replace)
        whole = whole or merged == t.content
        new_rec = FileRecord(BLOCKS, entry=t.entry, hash=content_hash(merged) if whole else None, blocks=kept)
        detail = "block " + ", ".join(updated) + " updated" + (f"; {'; '.join(skipped)}" if skipped else "")
        return Action(t, UPDATED, detail, merged, current, new_rec)
    new_rec = FileRecord(BLOCKS, entry=t.entry, hash=rec.hash if whole else None, blocks=kept)
    if skipped:
        return Action(t, SKIPPED, "; ".join(skipped) + " (skipped)", None, current, new_rec)
    if whole and current != t.content:  # sherpa's whole with an older seed outside the blocks (ADR-0022)
        new_rec = FileRecord(BLOCKS, entry=t.entry, hash=content_hash(t.content), blocks=hashes)
        return Action(t, UPDATED, "seed refreshed", t.content, current, new_rec)
    return Action(t, UNCHANGED, "unchanged", None, current, new_rec)


def _replace_blocks(text: str, replace: dict[str, str]) -> str:
    """One pass over the lines: inside a block that is being replaced, drop the old inner lines."""
    from sherpa.check import MARKER

    out, skip = [], False
    for line in text.split("\n"):
        m = MARKER.match(line)
        if m and m.group(1) == "begin" and m.group(2) in replace:
            out.append(line)
            out.extend(replace[m.group(2)].split("\n"))
            skip = True
            continue
        if m and m.group(1) == "end" and skip:
            skip = False
        if not skip:
            out.append(line)
    return "\n".join(out)


def _marked(t: Target, name: str) -> str:
    style = "#" if t.path.endswith((".yml", ".yaml")) else "html"
    inner = t.blocks[name]
    if style == "#":
        return f"# sherpa:begin {name}\n{inner}\n# sherpa:end {name}"
    return f"<!-- sherpa:begin {name} -->\n{inner}\n<!-- sherpa:end {name} -->"


def _plan_hooks(t: Target, current: str | None, rec: FileRecord | None) -> Action:
    if current is None:
        content = json.dumps({"hooks": t.hooks}, indent=2) + "\n"
        return Action(t, NEW, "new", content, None, FileRecord(JSON_HOOKS, entry=t.entry, hash=content_hash(content)))
    try:
        data = json.loads(current)
        if not isinstance(data, dict):
            raise ValueError("top level is not an object")
    except ValueError as e:
        return Action(t, SKIPPED, f"not valid JSON: {e} (skipped)", None, current, None)
    hooks = data.setdefault("hooks", {})
    added = []
    for event, groups in t.hooks.items():
        existing = hooks.setdefault(event, [])
        for group in groups:
            if not any(_has_sherpa_hook(g) for g in existing):
                existing.append(group)
                added.append(event)
    if not added:
        return Action(
            t,
            UNCHANGED,
            "hooks present",
            None,
            current,
            FileRecord(JSON_HOOKS, entry=t.entry, hash=content_hash(current)),
        )
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    return Action(
        t,
        UPDATED,
        "hooks added: " + ", ".join(added),
        content,
        current,
        FileRecord(JSON_HOOKS, entry=t.entry, hash=content_hash(content)),
    )


def _has_sherpa_hook(group: dict) -> bool:
    return any("sherpa-outcome.py" in str(h.get("command", "")) for h in group.get("hooks", []) if isinstance(h, dict))


# ---------------------------------------------------------------- phase 2: write, check, roll back

CHANGED_SINCE_PREVIEW = "changed since the preview (skipped)"


def _reconcile(a: Action, repo: Path) -> Action:
    """Compare-and-swap (ADR-0030): ``a.new`` was computed from ``a.old``; if the file no longer reads as
    ``a.old`` — an editor, a second agent — or a symlink appeared in its path (ADR-0031), writing ``a.new``
    would overwrite somebody's bytes. Skip instead and keep the previous record; the next run plans against
    what is there now."""
    if a.new is None and not a.delete:
        return a
    if _through_symlink(repo, a.path) or _read(repo / a.path) != a.old:
        return Action(a.target, SKIPPED, CHANGED_SINCE_PREVIEW, None, a.old, None)
    return a


def _roll_back(written: list[Action], repo: Path) -> list[str]:
    """Restore every written file to ``old`` (or remove it); returns the paths that could not be restored.
    Directories the run created go with their files — an empty ``.agents/`` and ``.claude/`` left behind made
    the next run ask which home to use, a question the rollback had caused (ADR-0032, amended)."""
    left = []
    for a in written:
        p = repo / a.path
        try:
            if a.old is None:
                p.unlink(missing_ok=True)
            else:
                _put(p, a.old, a.crlf)
        except OSError:
            left.append(a.path)
    _prune_empty_dirs(repo, [a.path for a in written if a.old is None and a.path not in left])
    return left


def _prune_empty_dirs(repo: Path, deleted: list[str]) -> None:
    """A directory that held nothing but a removed file goes with it, up to the repo root — git tracks no empty
    directory, so nothing of the user's is lost."""
    for rel in deleted:
        d = (repo / rel).parent
        while d != repo:
            try:
                d.rmdir()  # fails when not empty
            except OSError:
                break
            d = d.parent


INDEX_FILES = (
    ".sherpa/state.json",
    ".sherpa/harness-plan.yaml",
    ".sherpa/codebase-model.json",
    ".sherpa/telemetry/outcomes.ndjson",
)


def uninstall_index(repo: Path) -> tuple[list[str], list[str]]:
    """After ``apply --remove`` took the harness back: the index files and the telemetry go too, so a clean
    repository is clean again — ``git status --ignored`` empty (ADR-0048). Returns (removed, left): anything
    else under ``.sherpa/`` is not sherpa's and stays, named."""
    removed: list[str] = []
    for rel in INDEX_FILES:
        p = repo / rel
        if p.is_file():
            p.unlink()
            removed.append(rel)
    _prune_empty_dirs(repo, removed)
    sherpa_dir = repo / ".sherpa"
    left = [x.relative_to(repo).as_posix() for x in sherpa_dir.rglob("*") if x.is_file()] if sherpa_dir.is_dir() else []
    return removed, sorted(left)


def write(
    actions: list[Action],
    repo: Path,
    previous: State,
    plan: Plan,
    *,
    check: bool = True,
    home: str = "",
    targets: tuple[str, ...] = (),
) -> Result:
    from sherpa.check import FAIL
    from sherpa.check import check as run_check

    actions = [_reconcile(a, repo) for a in actions]
    ours = {a.path for a in actions if a.new is not None}  # scoped like the check after the write (ADR-0047)
    theirs = {a.path for a in actions if a.forget and not a.delete}  # handed back: yours now (ADR-0048)
    scope = {"managed_too": ours - theirs, "yours_now": theirs}
    before = {f for f in run_check(repo, **scope) if f.level == FAIL} if check else set()
    written: list[Action] = []
    result = Result(actions, previous)
    try:
        for a in actions:
            if a.delete:
                crlf = _uses_crlf(repo / a.path)
                (repo / a.path).unlink()  # ``old`` brings it back on rollback
                written.append(Action(a.target, a.op, a.detail, a.new, a.old, a.record, a.delete, a.forget, crlf))
                continue
            if a.new is None:
                continue
            crlf = a.old is not None and _uses_crlf(repo / a.path)  # an existing file keeps its line endings
            _put(repo / a.path, a.new, crlf)  # whole or not at all (ADR-0032)
            written.append(Action(a.target, a.op, a.detail, a.new, a.old, a.record, a.delete, a.forget, crlf))
    except OSError as e:
        result.error = f"{a.path}: {e}"
        result.rolled_back, result.left = True, _roll_back(written, repo)
        return result
    result.written = sum(not a.delete for a in written)
    result.removed = sum(a.delete for a in written)
    _prune_empty_dirs(repo, [a.path for a in written if a.delete])
    if check:
        result.findings = run_check(repo, **scope)
        new_fails = {f for f in result.findings if f.level == FAIL} - before
        if new_fails:
            result.rolled_back, result.left = True, _roll_back(written, repo)
            result.written = 0
            result.findings = sorted(new_fails, key=str)
            return result
    files = dict(previous.files)
    for a in actions:
        if a.record is not None:
            files[a.path] = a.record
        elif a.forget:
            files.pop(a.path, None)
    rev = state_mod.harness_rev(files)
    home, targets = home or previous.home, targets or previous.targets
    changed = (
        written
        or rev != previous.harness_rev
        or files != previous.files
        or (home, targets) != (previous.home, previous.targets)
    )
    result.state = State(
        harness_rev=rev,
        plan={k: str(v) for k, v in plan.model.items() if k in ("trunk", "rev", "as_of")},
        applied_at=state_mod.now_iso() if changed else previous.applied_at,
        files=files,
        home=home,
        targets=tuple(targets),
    )
    if changed:
        result.state.write(repo / state_mod.STATE_PATH)
    return result


# ---------------------------------------------------------------- console


def render_actions(actions: list[Action], plan: Plan) -> str:
    n = len(plan.entries)
    sel = len(selected(plan))  # the outcome entry counts too: its files carry no entry tag (F-e2e 0.8.1 §5)
    head = f"plan {plan.model.get('trunk', '?')}@{plan.model.get('rev', '?')[:10]}"
    lines = [f"sherpa apply — {head}: {n} entries, {sel} selected → {len(actions)} files"]
    w_path = min(max((len(a.path) for a in actions), default=10), 56)
    for a in actions:
        who = " ".join(a.target.entry.split(":")[:2]) if a.target.entry else "harness"
        lines.append(f"  {a.op} {a.path:<{w_path}}  {who:<28}  {a.detail}")
    c = {op: sum(a.op == op for a in actions) for op in (NEW, UPDATED, UNCHANGED, SKIPPED, REMOVED)}
    tail = f"{c[NEW]} to add, {c[UPDATED]} to change, {c[UNCHANGED]} unchanged, {c[SKIPPED]} skipped"
    lines.append(tail + (f", {c[REMOVED]} to remove." if c[REMOVED] else "."))
    return "\n".join(lines) + "\n"


def render_result(r: Result) -> str:
    from sherpa.check import FAIL

    n_fail = sum(f.level == FAIL for f in r.findings)
    n_warn = len(r.findings) - n_fail
    if r.rolled_back:
        if r.error is not None:
            lines = [f"write failed: {r.error} — rolled back, nothing written"]
        else:
            lines = [f"check: {n_fail} new FAIL — rolled back, nothing written"]
            lines.extend(f"  {f}" for f in r.findings)
        if r.left:
            lines.append(
                "rollback failed for: " + ", ".join(r.left) + " — restore with `git checkout -- <path>` or "
                "`git clean`, then `sherpa adopt` rebuilds the state"
            )
        return "\n".join(lines) + "\n"
    lines = [f"check: {n_fail} FAIL, {n_warn} WARN"]
    lines.extend(f"  {f}" for f in r.findings if f.level == FAIL)
    lines.extend(f"  ! {a.path}  {a.detail}" for a in r.actions if a.detail == CHANGED_SINCE_PREVIEW)
    what = f"{r.written} files written" + (f", {r.removed} removed" if r.removed else "")
    lines.append(f"{what} · harness_rev {r.state.harness_rev} → .sherpa/state.json")
    return "\n".join(lines) + "\n"


__all__ = [
    "CHANGED_SINCE_PREVIEW",
    "HOOK_COMMAND",
    "INDEX_FILES",
    "REMOVED",
    "THROUGH_SYMLINK",
    "Action",
    "Result",
    "StalePlan",
    "plan_files",
    "render_actions",
    "render_result",
    "targets_for",
    "uninstall_index",
    "write",
]
