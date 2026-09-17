"""Plan entry → files. Pure: (plan, model, sherpa version) → targets; no clock, no file system, sorted output.

Every generated markdown file follows the owner principle from harness practice: **facts have exactly one owner**
(the owner doc), agents and skills only point there. Sherpa owns marked blocks — the scanner facts, the knowledge
manifest, the generator facts — and regenerates them on every apply; everything outside a block is seeded once
and belongs to the humans (ADR-0013). Dates inside blocks come from the model (``as_of``), never from a clock.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from sherpa import __version__
from sherpa.apply.state import BLOCKS, JSON_HOOKS, MANAGED
from sherpa.config import TARGETS
from sherpa.model import DirStat, Model, ModuleStat
from sherpa.plan import PROPOSE, Entry, Plan

ASSETS = Path(__file__).parent / "assets"
CLAUDE = ".claude"
AGENTS = f"{CLAUDE}/agents"
SETTINGS = f"{CLAUDE}/settings.json"
OUTCOME_HOOK = f"{CLAUDE}/hooks/sherpa-outcome.py"
TELEMETRY_IGNORE = ".sherpa/telemetry/.gitignore"
CHECK_SCRIPT_NAME = "sherpa-check.py"
HOOK_EVENTS = (
    ("UserPromptSubmit", ""),
    ("PostToolUse", "Bash|Edit|Write|MultiEdit"),
    ("PostToolUseFailure", "Bash"),
    ("Stop", ""),
)
# python3 first (Linux/macOS), python as the fallback (Windows launchers); the script itself is stdlib-only.
HOOK_COMMAND = (
    'sh -c \'command -v python3 >/dev/null 2>&1 && exec python3 "$0" || exec python "$0"\' '
    '"$CLAUDE_PROJECT_DIR/' + OUTCOME_HOOK + '"'
)


def check_script(home: str) -> str:
    return f"{home}/scripts/{CHECK_SCRIPT_NAME}"


@dataclass(frozen=True)
class Target:
    path: str  # repo-relative, "/" separated
    mode: str  # managed | blocks | json-hooks
    entry: str | None  # "kind/target/scope" — None for base files
    content: str = ""  # managed: the file; blocks: the seed (markers included)
    blocks: dict[str, str] = field(default_factory=dict)  # blocks: name → inner text
    hooks: dict[str, list[dict]] = field(default_factory=dict)  # json-hooks: event → hook entries to merge
    append: bool = False  # blocks: when the file exists without our markers, append them (CLAUDE.md)


def entry_key(e: Entry) -> str:
    """State key of an entry; ":" because targets may contain "/" (Go module paths)."""
    return f"{e.kind}:{e.target}:{e.scope}"


def selected(plan: Plan) -> list[Entry]:
    """Terraform model: every proposal unless rejected, every no that was accepted. An entry covered by an adopted
    file (ADR-0007) is rendered only when a human accepts it explicitly — a second agent for the same unit is a
    decision, never a default."""
    return [
        e
        for e in plan.entries
        if e.decision == "accept" or (e.default == PROPOSE and e.decision != "reject" and not e.covered)
    ]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "root"


# ---------------------------------------------------------------- blocks


def html_block(name: str, inner: str) -> str:
    return f"<!-- sherpa:begin {name} -->\n{inner}\n<!-- sherpa:end {name} -->"


def yaml_block(name: str, inner: str) -> str:
    return f"# sherpa:begin {name}\n{inner}\n# sherpa:end {name}"


def _table(rows: list[tuple[str, str]]) -> str:
    return "\n".join(["| field | value |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rows])


def _list(items: list[str], empty: str = "—") -> str:
    return ", ".join(f"`{i}`" for i in items) if items else empty


class Renderer:
    """One neutral core (owner docs, skills, checker copy under ``home``) and one adapter per runtime target
    (ADR-0015): ``claude`` = agents, hooks, ``CLAUDE.md`` root and nested; ``agents-md`` = ``AGENTS.md`` root and
    nested. Every unit gets a proximity file per target so the runtime loads its facts when working there."""

    def __init__(
        self,
        plan: Plan,
        model: Model,
        version: str = __version__,
        *,
        home: str = ".agents",
        targets: tuple[str, ...] = TARGETS,
    ) -> None:
        self.plan, self.model, self.version = plan, model, version
        self.home, self.runtime_targets = home, tuple(targets)
        self.modules = {m.id: m for m in model.modules}
        self.dirs = {d.path: d for d in model.git.dirs}
        # No sherpa version in the stamp: an upgrade must not rewrite every facts block in the repo.
        self.stamp = f"{model.git.trunk.ref}@{model.git.trunk.rev[:10]}, as of {model.git.windows.as_of[:10]}"
        self.entries = selected(plan)
        self.slugs = self._slugs()
        self.units = [e for e in self.entries if e.kind in ("owner-doc", "test-infra")]
        self.docs = {e.target: self.doc_path(e) for e in self.units}  # unit → owner doc path
        # A unit whose owner doc is an adopted file (ADR-0007): no doc is rendered, agents and proximity files
        # point at the adopted one, and the proximity files still carry the measured facts.
        for e in plan.entries:
            if e.kind in ("owner-doc", "test-infra") and e.covered and e not in self.entries:
                self.units.append(e)
                self.docs[e.target] = e.covered

    # ------------------------------------------------------------ naming

    def _slugs(self) -> dict[str, str]:
        """entry key → file slug; a collision (two units with the same slug) gets the scope appended."""
        by_slug: dict[tuple[str, str], list[Entry]] = {}
        for e in self.entries:
            by_slug.setdefault((e.kind, slug(e.target)), []).append(e)
        out: dict[str, str] = {}
        for (_, s), es in by_slug.items():
            for e in es:
                out[entry_key(e)] = s if len(es) == 1 else f"{s}--{slug(e.scope)}"
        return out

    def doc_path(self, e: Entry) -> str:
        return f"{self.home}/docs/modules/{self.slugs[entry_key(e)]}.md"

    def skill_path(self, e: Entry) -> str:
        return f"{self.home}/skills/{self.slugs[entry_key(e)]}/SKILL.md"

    def librarian_path(self, e: Entry) -> str:
        return f"{self.home}/skills/{self.slugs[entry_key(e)]}-sync/SKILL.md"

    # ------------------------------------------------------------ composition

    def targets(self) -> list[Target]:
        out = list(self.core_targets())
        if "claude" in self.runtime_targets:
            out.extend(self.claude_targets())
        if "agents-md" in self.runtime_targets:
            out.extend(self.agents_md_targets())
        out.sort(key=lambda t: t.path)
        return out

    def core_targets(self) -> list[Target]:
        """Runtime-neutral: owner docs, skills, the checker copy, the telemetry ignore file."""
        from sherpa import check

        check_src = _stamped(Path(check.__file__).read_text(encoding="utf-8"), self.version)
        out = [
            Target(check_script(self.home), MANAGED, None, check_src),
            Target(TELEMETRY_IGNORE, MANAGED, None, "*\n!.gitignore\n"),
        ]
        for e in self.entries:
            if e.kind in ("owner-doc", "test-infra"):
                out.append(self.owner_doc(e))
            elif e.kind == "librarian":
                out.append(self.librarian(e, self.docs.get(e.target)))
            elif e.kind == "skill":
                out.append(self.skill(e))
        return out

    # ------------------------------------------------------------ target: claude

    def claude_targets(self) -> list[Target]:
        """Claude Code: subagents, the outcome hook (the only runtime with hooks), CLAUDE.md root and nested,
        and — when the core lives elsewhere — a stub per skill so ``.claude/skills/`` still lists it."""
        hook_src = _stamped((ASSETS / "sherpa-outcome.py").read_text(encoding="utf-8"), self.version)
        hooks = {
            event: [{"matcher": matcher, "hooks": [{"type": "command", "command": HOOK_COMMAND, "timeout": 10}]}]
            if matcher
            else [{"hooks": [{"type": "command", "command": HOOK_COMMAND, "timeout": 10}]}]
            for event, matcher in HOOK_EVENTS
        }
        out = [
            Target(OUTCOME_HOOK, MANAGED, None, hook_src),
            Target(SETTINGS, JSON_HOOKS, None, hooks=hooks),
            self.root_file("CLAUDE.md", self.claude_md_overview()),
        ]
        for e in self.entries:
            if e.kind == "agent":
                out.append(self.agent(e, self.docs.get(e.target)))
        for e in self.units:
            if e.scope:
                out.append(self.nested_claude_md(e))
        if self.home != CLAUDE:
            for e in self.entries:
                if e.kind in ("skill", "librarian"):
                    out.append(self.skill_stub(e))
        return out

    def claude_md_overview(self) -> str:
        return "\n".join(
            [
                "## AI harness (managed by sherpa)",
                "",
                f"Module facts live in `{self.home}/docs/modules/` — one owner doc per module, the single place",
                "for a fact. Agents in `.claude/agents/` carry a role and a knowledge manifest, never facts;",
                f"skills in `{self.home}/skills/` are procedures. Blocks between `sherpa:begin` and `sherpa:end`",
                "markers are regenerated by `sherpa apply` — write outside them. Integrity: `sherpa status`",
                f"or `python3 {check_script(self.home)}`.",
            ]
        )

    def root_file(self, name: str, overview: str) -> Target:
        """Root CLAUDE.md / AGENTS.md: seeded with a title, appended to when it exists. A new CLAUDE.md in a
        repo that has (or gets) AGENTS.md imports it — the cross-tool file stays the source."""
        block = html_block("harness", overview)
        head = f"# {self.model.repo}\n\n"
        if name == "CLAUDE.md" and (self.has_file("AGENTS.md") or "agents-md" in self.runtime_targets):
            head += "@AGENTS.md\n\n"
        return Target(name, BLOCKS, None, f"{head}{block}\n", {"harness": overview}, append=True)

    def has_file(self, path: str) -> bool:
        return any(f.path == path for f in self.model.git.files)

    def nested_claude_md(self, e: Entry) -> Target:
        """Claude Code loads a subdirectory's CLAUDE.md when it works there — the same proximity AGENTS.md has.
        With the agents-md target on, the file imports its sibling instead of repeating the facts."""
        inner = "@AGENTS.md" if "agents-md" in self.runtime_targets else self.proximity_block(e)
        block = html_block("harness", inner)
        return Target(f"{e.scope}/CLAUDE.md", BLOCKS, entry_key(e), f"{block}\n", {"harness": inner}, append=True)

    def skill_description(self, e: Entry) -> str:
        if e.kind == "librarian":
            return (
                f"Keep the owner doc of {e.target} in sync with the code: run on a schedule or after larger "
                f"merges to {e.scope or '.'}."
            )
        title = str(e.evidence.get("title", e.target.removeprefix("regenerate-")))
        return (
            f"Regenerate {title} output in {e.scope or '.'} instead of editing generated files. Use when a "
            "change touches the sources or configs listed in this skill."
        )

    def skill_stub(self, e: Entry) -> Target:
        real = self.skill_path(e) if e.kind == "skill" else self.librarian_path(e)
        name = real.split("/")[-2]
        stub_dir = f"{CLAUDE}/skills/{name}"
        content = "\n".join(
            [
                "---",
                f"name: {name}",
                "description: " + _quoted(self.skill_description(e)),
                "---",
                "",
                f"This skill lives in [{real}]({_relpath(stub_dir, real)}) — read and follow that file.",
                "(Stub managed by sherpa: the skill is runtime-neutral, Claude Code lists it from here.)",
                "",
            ]
        )
        return Target(f"{stub_dir}/SKILL.md", MANAGED, entry_key(e), content)

    # ------------------------------------------------------------ target: agents-md

    def agents_md_targets(self) -> list[Target]:
        """The cross-tool convention (Codex, Cursor, Gemini CLI, Copilot, Jules, …): the closest AGENTS.md wins,
        so every unit gets one with its facts; the root file carries the overview and the index."""
        nested = [e for e in self.units if e.scope]
        root_units = [e for e in self.units if not e.scope]
        lines = [
            "## AI harness (managed by sherpa)",
            "",
            f"Module facts live in `{self.home}/docs/modules/` (one owner doc per module, the single place for a",
            f"fact); procedures in `{self.home}/skills/`. Blocks between `sherpa:begin` and `sherpa:end` markers",
            "are regenerated by `sherpa apply` — write outside them. Integrity: `sherpa status` or",
            f"`python3 {check_script(self.home)}`.",
        ]
        if nested:
            lines += ["", "Nearest AGENTS.md per module (loaded when you work there):", ""]
            lines += [f"- `{e.scope}/AGENTS.md` — {e.target}" for e in sorted(nested, key=lambda e: e.scope)]
        for e in root_units:
            lines += ["", self.proximity_block(e)]
        out = [self.root_file("AGENTS.md", "\n".join(lines))]
        for e in nested:
            inner = self.proximity_block(e)
            block = html_block("facts", inner)
            out.append(
                Target(f"{e.scope}/AGENTS.md", BLOCKS, entry_key(e), f"{block}\n", {"facts": inner}, append=True)
            )
        return out

    def proximity_block(self, e: Entry) -> str:
        """Short facts for the runtime that lands in this directory — the owner doc stays the place for detail."""
        u = self.unit(e)
        doc = self.docs.get(e.target)
        what = "test infrastructure" if e.kind == "test-infra" else "module"
        rows: list[tuple[str, str]] = [("unit", f"`{e.target}` ({what})")]
        if isinstance(u, ModuleStat):
            rows += [
                ("depends on", _list(u.deps)),
                ("dependents", _list(u.dependents, "none in the repo — changes here stay local")),
                ("tested by", _list(u.tested_by, "no test module found")),
                ("hotspots", _list(u.hotspots[:3])),
            ]
        gens = self.generator_skills(e)
        if gens:
            rows.append(("generated code", ", ".join(f"{fam} → `{p}` (never edit the output)" for fam, p in gens)))
        lines = [f"## {e.target} (managed by sherpa, {self.stamp})", "", _table(rows), ""]
        if doc:
            lines.append(
                f"Read the owner doc [{doc}]({_relpath(e.scope, doc)}) before answering questions about this unit; "
                "facts live there, not here."
            )
        return "\n".join(lines)

    # ------------------------------------------------------------ facts

    def unit(self, e: Entry) -> ModuleStat | DirStat | None:
        return self.modules.get(e.target) or self.dirs.get(e.scope)

    def generator_skills(self, e: Entry) -> list[tuple[str, str]]:
        """(family, skill path) for generators owned by this unit that the plan turns into skills."""
        out = []
        for s in self.entries:
            if s.kind != "skill":
                continue
            owned = s.evidence.get("module") == e.target if s.evidence.get("module") else _below(str(s.scope), e.scope)
            if owned:
                out.append((str(s.evidence.get("family", s.target)), self.skill_path(s)))
        return sorted(set(out))

    def facts_rows(self, e: Entry) -> list[tuple[str, str]]:
        u = self.unit(e)
        rows: list[tuple[str, str]] = [("path", f"`{e.scope or '.'}`")]
        if isinstance(u, ModuleStat):
            rows += [
                ("kind", f"{u.kind} module (`{u.manifest}`)" + (", test module" if u.is_test else "")),
                (
                    "files / LOC",
                    f"{u.files} / {u.loc}" + (f" ({u.generated_files} generated)" if u.generated_files else ""),
                ),
                ("commits 90d / 30d", f"{u.commits_90d} / {u.commits_30d} · {u.authors_90d} authors"),
                ("depends on", _list(u.deps)),
                ("dependents", _list(u.dependents)),
                ("tested by", _list(u.tested_by)),
                ("hotspots", _list(u.hotspots[:3])),
            ]
        elif isinstance(u, DirStat):
            rows += [
                ("kind", "directory without a module manifest"),
                (
                    "files / LOC",
                    f"{u.files} / {u.loc}" + (f" ({u.generated_files} generated)" if u.generated_files else ""),
                ),
                ("commits 90d / 30d", f"{u.commits_90d} / {u.commits_30d} · {u.authors_90d} authors"),
            ]
        else:  # unit vanished from the model — the plan is stale, apply refuses earlier; keep the evidence
            rows += [(k, f"{v}") for k, v in sorted(e.evidence.items()) if k != "path"]
        gens = self.generator_skills(e)
        if gens:
            docs_dir = f"{self.home}/docs/modules"
            rows.append(("generators", ", ".join(f"{fam} → [skill]({_relpath(docs_dir, p)})" for fam, p in gens)))
        return rows

    # ------------------------------------------------------------ files

    def owner_doc(self, e: Entry) -> Target:
        facts = "\n".join([f"## facts ({self.stamp})", "", _table(self.facts_rows(e))])
        what = "test infrastructure" if e.kind == "test-infra" else "module"
        seed = "\n".join(
            [
                f"# {e.target} — owner doc",
                "",
                f"> Owner of every fact about the {what} `{e.target}`. Agents and skills link here instead of",
                "> copying (owner principle). Keep anchor headings small and stable — links hang on them.",
                "",
                html_block("facts", facts),
                "",
                "## structure",
                "",
                "<!-- what the module is made of — directories, entry points, boundaries; only as deep as needed -->",
                "",
                "## rules",
                "",
                "<!-- module-specific MUST rules as a table: rule | consequence. Global rules belong elsewhere. -->",
                "",
                "## key services",
                "",
                "<!-- | class | source `path:line` | purpose | — semantics, never a copied model -->",
                "",
                "## references",
                "",
                "<!-- procedures (skills), the agent, related owner docs -->",
                "",
            ]
        )
        return Target(self.doc_path(e), BLOCKS, entry_key(e), seed, {"facts": facts})

    def agent(self, e: Entry, doc: str | None) -> Target:
        u = self.unit(e)
        name = self.slugs[entry_key(e)]
        doc_rel = _relpath(AGENTS, doc) if doc else None
        doc_text = doc
        always = [_relpath(CLAUDE, doc)] if doc else []
        on_demand = [_relpath(CLAUDE, p) for _, p in self.generator_skills(e)]
        knowledge = "\n".join(["knowledge:", *_yaml_list("always", always), *_yaml_list("on_demand", on_demand)])
        deps = u.dependents if isinstance(u, ModuleStat) else []
        doc_link = f"[{doc_text}]({doc_rel})" if doc_rel else "the owner doc"
        manifest = "\n".join(
            [
                "## Knowledge manifest",
                "",
                f"Read first: {doc_link if doc_rel else 'the owner doc, once the plan has one'}.",
                f"Dependents that see your changes: {_list(deps, 'none in the repo')}.",
                f"Scope: `{e.scope or '.'}` ({self.stamp}).",
            ]
        )
        seed = "\n".join(
            [
                "---",
                f"name: {name}",
                "description: "
                + _quoted(
                    f"Use this agent for work in {e.scope or '.'} ({e.target}). Trigger: changes to that path, "
                    f"questions about {e.target}. NOT for: other modules — their owner docs and agents apply."
                ),
                yaml_block("knowledge", knowledge),
                "---",
                "",
                f"# {e.target} — agent",
                "",
                f"> Role: expert for `{e.target}` (`{e.scope or '.'}`). Facts do NOT live in this file — they live in",
                f"> {doc_link}; cite from there instead of from memory.",
                "",
                html_block("manifest", manifest),
                "",
                "## How to work",
                "",
                "1. Read the owner doc before answering; quote its anchors instead of memory.",
                "2. Code beats doc — report the difference as a finding, do not silently rewrite the doc.",
                "3. Outside the scope: hand off to the owner doc or agent of that module instead of guessing.",
                "",
                "## Handoff contract",
                "",
                "Every answer ends with four sections: `conclusion` (short prose) · `artefacts` (paths and anchors,",
                "no full text) · `open` (assumptions, risks, decisions) · `evidence` (owner anchor or `path:line`",
                "per factual claim).",
                "",
            ]
        )
        return Target(f"{AGENTS}/{name}.md", BLOCKS, entry_key(e), seed, {"knowledge": knowledge, "manifest": manifest})

    def librarian(self, e: Entry, doc: str | None) -> Target:
        u = self.unit(e)
        name = f"{self.slugs[entry_key(e)]}-sync"
        c30 = u.commits_30d if u else e.evidence.get("commits_30d", 0)
        cadence = "weekly" if int(c30) >= 30 else "every two weeks"
        doc_rel = _relpath(self.librarian_path(e).rsplit("/", 1)[0], doc) if doc else None
        doc_text = doc
        scope = "\n".join(
            [
                "## Scope",
                "",
                f"- pathspec: `{e.scope or '.'}` — {c30} commits/30d, suggested cadence: {cadence}",
                f"- owner doc: {f'[{doc_text}]({doc_rel})' if doc_rel else 'none in the plan yet'}",
                "- the facts block in the owner doc is regenerated by `sherpa apply` — never edit it by hand",
                f"- scanned: {self.stamp}",
            ]
        )
        seed = "\n".join(
            [
                "---",
                f"name: {name}",
                "description: " + _quoted(self.skill_description(e)),
                "---",
                "",
                f"# {e.target} — librarian",
                "",
                html_block("scope", scope),
                "",
                "## Procedure",
                "",
                "1. `git log --since=<last run> --no-merges origin/<trunk> -- <pathspec>` — what changed, by whom.",
                "2. For every human section of the owner doc: does the code still say this? Verify against the",
                "   source, never against memory.",
                "3. Correct facts in the owner doc; contradictions you cannot resolve get `[REVIEW NEEDED: …]`",
                "   in place. Never touch the facts block.",
                "4. Record the run: date, commits reviewed, facts corrected, open reviews.",
                "",
                "## Done when",
                "",
                "Every fact in the owner doc has been verified against the current code or is marked for review.",
                "",
            ]
        )
        return Target(self.librarian_path(e), BLOCKS, entry_key(e), seed, {"scope": scope})

    def skill(self, e: Entry) -> Target:
        ev = e.evidence
        family = str(ev.get("family", e.target.removeprefix("regenerate-")))
        title = str(ev.get("title", family))
        name = self.slugs[entry_key(e)]
        facts = "\n".join(
            [
                f"## facts ({self.stamp})",
                "",
                _table(
                    [
                        ("family", f"{title} (`{family}`)"),
                        ("home", f"`{e.scope or '.'}`"),
                        ("generated files", f"{ev.get('generated_files', 0)} ({ev.get('generated_loc', 0)} LOC)"),
                        ("sources", _list([str(s) for s in ev.get("sources", [])])),
                        ("configs", _list([str(c) for c in ev.get("configs", [])])),
                        ("command", f"`{ev.get('command', '')}`" if ev.get("command") else "—"),
                    ]
                ),
            ]
        )
        seed = "\n".join(
            [
                "---",
                f"name: {name}",
                "description: " + _quoted(self.skill_description(e)),
                "---",
                "",
                f"# {name}",
                "",
                "> Generated code is regenerated, not explained (ADR-0011): the knowledge lives in the sources and the",
                "> generator, never in the output.",
                "",
                html_block("facts", facts),
                "",
                "## Procedure",
                "",
                "1. Change the source (model, schema, proto, config) — never the generated files.",
                "2. Run the command from the facts table from the home directory; commit sources and output together.",
                "3. Review the generated diff for surprises (renames, dropped columns, breaking changes).",
                "",
                "## Don't",
                "",
                "- Hand-edit a generated file: the next run overwrites it, and the fix is lost silently.",
                "- Explain generated code in an owner doc — point to this skill instead.",
                "",
            ]
        )
        return Target(self.skill_path(e), BLOCKS, entry_key(e), seed, {"facts": facts})


def _stamped(src: str, version: str) -> str:
    return src.replace('SHERPA_VERSION = "dev"', f'SHERPA_VERSION = "{version}"', 1)


def _quoted(text: str) -> str:
    """A double-quoted YAML scalar; module ids may carry quotes or colons."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _yaml_list(key: str, items: list[str]) -> list[str]:
    return [f"  {key}: []"] if not items else [f"  {key}:", *(f"    - {i}" for i in items)]


def _below(path: str, scope: str) -> bool:
    return bool(scope) and (path == scope or path.startswith(scope + "/"))


def _inner(block: str) -> str:
    return "\n".join(block.split("\n")[1:-1])


def _relpath(from_dir: str, to_path: str) -> str:
    """Relative markdown link from a directory to a file, "/" separated (no os.path on Windows)."""
    a, b = from_dir.split("/"), to_path.split("/")
    i = 0
    while i < min(len(a), len(b) - 1) and a[i] == b[i]:
        i += 1
    return "/".join([".."] * (len(a) - i) + b[i:])


def hooks_json(hooks: dict[str, list[dict]]) -> str:
    return json.dumps({"hooks": hooks}, indent=2) + "\n"
