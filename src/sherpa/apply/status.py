"""``sherpa status`` — drift, checker findings and outcome labels in one screen; exit 1 only on a checker FAIL.

Drift is what ``apply`` would do now: ``~`` pending updates (a new scan changed the facts), ``!`` hand edits
and broken markers, ``-`` files in the state that vanished, ``?`` orphans (in the state, no longer in the plan).
Outcome labels come from ``.sherpa/telemetry/outcomes.ndjson`` (hook, ADR-0008), grouped by ``harness_rev``;
the evaluation proper (trend, regression between versions) is M5.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from sherpa import __version__
from sherpa.apply.render import check_script
from sherpa.apply.state import ADOPTED, State
from sherpa.check import FAIL, Finding
from sherpa.check import check as run_check

MISSING, ORPHAN = "-", "?"
OUTCOMES = Path(".sherpa") / "telemetry" / "outcomes.ndjson"
_VERSION = re.compile(r'^SHERPA_VERSION = "([^"]+)"', re.M)


@dataclass
class Report:
    harness_rev: str
    applied_at: str
    drift: list[tuple[str, str, str]] = field(default_factory=list)  # (op, path, detail)
    findings: list[Finding] = field(default_factory=list)
    outcomes: dict[str, Counter] = field(default_factory=dict)  # harness_rev → label counts
    corrections: int = 0
    notes: list[str] = field(default_factory=list)
    stale: tuple[str, str, str] | None = None  # (trunk, plan rev, current rev) when the trunk moved since the plan

    @property
    def fails(self) -> int:
        return sum(f.level == FAIL for f in self.findings)


def report(repo: Path, state: State, actions: list, *, stale: tuple[str, str, str] | None = None) -> Report:
    from sherpa.apply import NEW, SKIPPED, UPDATED

    r = Report(state.harness_rev or "none", state.applied_at or "never", stale=stale)
    targeted = {a.path for a in actions}
    adopted = {path for path, rec in state.files.items() if rec.origin == ADOPTED}
    missing = {path for path in state.files if not (repo / path).is_file()}
    for a in actions:
        if a.path in adopted:
            continue  # yours (ADR-0007): listed below only when gone
        if a.path in missing:
            r.drift.append((MISSING, a.path, "in the state, not on disk — apply recreates it"))
        elif a.op in (NEW, UPDATED, SKIPPED):
            r.drift.append((a.op, a.path, a.detail))
    for path in sorted(state.files):
        if path in adopted:
            if path in missing:
                r.drift.append((MISSING, path, "adopted file is gone — `sherpa adopt` drops the record"))
        elif path in missing and path not in targeted:
            r.drift.append((MISSING, path, "in the state, not on disk — `sherpa adopt` drops the record"))
        elif path not in targeted:
            r.drift.append((ORPHAN, path, "in the state, no longer in the plan"))
    if adopted:
        r.notes.append(f"{len(adopted)} adopted files are yours and never touched (ADR-0007)")
    r.drift.sort(key=lambda d: d[1])
    r.findings = [f for f in run_check(repo) if f.rule != "C8"]  # drift above is the same information, sharper
    r.outcomes, r.corrections = _outcomes(repo / OUTCOMES)
    script = check_script(state.home or ".claude")
    deployed = _deployed_version(repo / script)
    if deployed and deployed != __version__:
        r.notes.append(f"{script} is sherpa {deployed}, installed is {__version__} — `sherpa apply` refreshes it")
    return r


def _deployed_version(path: Path) -> str | None:
    if not path.is_file():
        return None
    m = _VERSION.search(path.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else None


def _outcomes(path: Path) -> tuple[dict[str, Counter], int]:
    per_rev: dict[str, Counter] = {}
    corrections = 0
    if not path.is_file():
        return per_rev, corrections
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("kind") == "correction":
            corrections += 1
        elif rec.get("kind") == "outcome":
            per_rev.setdefault(str(rec.get("harness_rev", "none")), Counter())[str(rec.get("label", "unknown"))] += 1
    return per_rev, corrections


def render(r: Report) -> str:
    lines = [f"sherpa status — harness_rev {r.harness_rev}, applied {r.applied_at}"]
    if r.stale:
        trunk, rev, now = r.stale
        lines.append(f"plan: stale — {trunk} moved {rev[:10]} → {now[:10]} since `sherpa plan`; run `sherpa plan`")
    else:
        lines.append("plan: current")
    if r.drift:
        w = min(max(len(p) for _, p, _ in r.drift), 56)
        lines.append(f"drift: {len(r.drift)} files")
        lines.extend(f"  {op} {path:<{w}}  {detail}" for op, path, detail in r.drift)
    else:
        lines.append("drift: none — files match the state and the plan")
    n_warn = len(r.findings) - r.fails
    lines.append(f"check: {r.fails} FAIL, {n_warn} WARN")
    lines.extend(f"  {f}" for f in r.findings)
    if r.outcomes:
        total = sum(sum(c.values()) for c in r.outcomes.values())
        lines.append(
            f"outcomes: {total} executions labelled" + (f", {r.corrections} corrections" if r.corrections else "")
        )
        for rev, c in sorted(r.outcomes.items(), key=lambda kv: (kv[0] != r.harness_rev, kv[0])):
            mark = " (current)" if rev == r.harness_rev else ""
            counts = ", ".join(f"{c.get(label, 0)} {label}" for label in ("success", "failed", "unknown"))
            lines.append(f"  {rev}{mark}: {counts}")
    else:
        lines.append("outcomes: none yet — labels appear once Claude Code runs with the hook installed")
    lines.extend(f"  note: {n}" for n in r.notes)
    return "\n".join(lines) + "\n"


def render_json(r: Report) -> str:
    """The same report for scripts (``sherpa status --json``); exit code unchanged."""
    out = {
        "sherpa": __version__,
        "harness_rev": r.harness_rev,
        "applied_at": r.applied_at,
        "plan": {"stale": r.stale is not None}
        | ({"trunk": r.stale[0], "plan_rev": r.stale[1], "current_rev": r.stale[2]} if r.stale else {}),
        "drift": [{"op": op, "path": path, "detail": detail} for op, path, detail in r.drift],
        "findings": [asdict(f) for f in r.findings],
        "outcomes": {rev: dict(c) for rev, c in sorted(r.outcomes.items())},
        "corrections": r.corrections,
        "notes": list(r.notes),
    }
    return json.dumps(out, indent=2, ensure_ascii=False) + "\n"
