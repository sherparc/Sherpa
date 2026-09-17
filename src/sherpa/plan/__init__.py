"""``sherpa plan`` stage 1 — deterministic rules over the codebase model → ``harness-plan``.

Every entry carries ``evidence`` (model fields only), ``checks`` (each criterion with ✓/✗), ``cost`` and, for
``skip``, a ``reason`` with a flip criterion. Thresholds are rank **and** floor (ADR-0006); rules in ``rules``,
file format in ``yamlio`` (ADR-0005), principles in ADR-0011/0012.

Determinism: same model + same config → byte-identical YAML. No LLM, no clock.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sherpa import __version__
from sherpa.config import PlanConfig
from sherpa.model import Model

PLAN_SCHEMA_VERSION = 1
KINDS = ("outcome", "owner-doc", "agent", "librarian", "test-infra", "skill")
PROPOSE, SKIP = "propose", "skip"
DECISIONS = ("accept", "reject")
OK, FAIL = "✓", "✗"


@dataclass(frozen=True)
class Check:
    label: str  # the measurement, short: "rank 1/12 churn", "214 commits/90d"
    ok: bool
    need: str = ""  # the criterion: "rank ≤ 3 by commits/90d" — empty when there is none (mandatory entries)

    @property
    def short(self) -> str:
        return f"{self.label} {OK if self.ok else FAIL}"

    def __str__(self) -> str:
        return f"{self.label} ({self.need}) {OK if self.ok else FAIL}" if self.need else self.short


@dataclass(frozen=True)
class Entry:
    kind: str
    target: str  # module id, directory, repo name or skill name
    scope: str  # path in the repo ("" = root)
    default: str  # propose | skip
    evidence: dict[str, object]  # model fields only
    checks: tuple[Check, ...]
    cost: str
    reason: str | None = None  # skip only: what is missing + flip criterion
    decision: str | None = None  # set by a human: accept | reject; survives a re-plan
    covered: str | None = None  # path of an adopted file that already fills this entry (ADR-0007); from the state

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.kind, self.target, self.scope)

    @property
    def summary(self) -> str:
        """Console line; skills are named after their family, so their location comes first."""
        parts = [c.short for c in self.checks]
        if self.kind == "skill":
            parts.insert(0, self.scope or ".")
        return " · ".join(parts)


@dataclass(frozen=True)
class Plan:
    repo: str
    model: dict[str, str]  # trunk, rev, as_of, sherpa
    thresholds: dict[str, float | int]
    ranking: dict[str, list[str]]  # commits_90d / commits_30d → units, descending
    entries: list[Entry]
    sherpa: str = __version__
    schema_version: int = PLAN_SCHEMA_VERSION
    notes: list[str] = field(default_factory=list)  # what the reader must see (dormant units, …)

    def counts(self) -> tuple[int, int]:
        return (
            sum(e.default == PROPOSE for e in self.entries),
            sum(e.default == SKIP for e in self.entries),
        )


def build_plan(model: Model, cfg: PlanConfig | None = None) -> Plan:
    from sherpa.plan.rules import build

    return build(model, cfg or PlanConfig())


def render_console(plan: Plan, out_name: str) -> str:
    """Console view like ``terraform plan``: summary, then ``+`` proposals and ``-`` reasoned no's."""
    n_yes, n_no = plan.counts()
    lines = [f"{out_name} — {n_yes} proposals, {n_no} reasoned no's"]
    if plan.entries:
        w_kind = max(len(e.kind) for e in plan.entries)
        w_target = min(max(len(e.target) for e in plan.entries), 48)
        for e in plan.entries:
            sign = "+" if e.default == PROPOSE else "-"
            mark = f" [{e.decision}]" if e.decision else ""
            if e.covered:
                mark += f" [covered by {e.covered}]"
            lines.append(f"  {sign} {e.kind:<{w_kind}}  {e.target:<{w_target}}  {e.summary}{mark}")
    lines.extend(f"  {n}" for n in plan.notes)
    return "\n".join(lines) + "\n"


__all__ = [
    "DECISIONS",
    "KINDS",
    "PROPOSE",
    "SKIP",
    "Check",
    "Entry",
    "Plan",
    "build_plan",
    "render_console",
]
