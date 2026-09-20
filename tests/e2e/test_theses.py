"""The theses, in lifecycle order — one test per claim, the claim in the ``thesis`` marker, the proving line
in ``ev``. T01–T22 are the catalogue of the ``e2e-test`` skill; E01–E05 are the follow-ups of its first runs
(the deployed checker standalone, the write boundary, the configured home, line endings, a dangling symlink),
E06–E09 the claims of M3j's second slice (a decision follows a renamed unit, a dropped one is named, the WARN
count of ``apply`` is ``check``'s, the uninstall names the state once), E10–E12 the claims of M3l (a revision
that survives a tool upgrade, the C7 ceiling for the team's files, git-ignored files are not the harness).

Every assertion compares what a user sees — exit code, stdout, stderr, the files on disk, ``git status`` —
never an internal. Numbers are relative (more than none, the same twice), so the same test holds on the
built-in monorepo and on a corpus of twenty thousand files."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.e2e.conftest import Run, Sherpa, Store, git, git_status, home_dirs, require, rmtree

thesis = pytest.mark.thesis
ACTION = re.compile(r"^  ([+~=!-]) (\S+)\s")
README = Path(__file__).resolve().parents[2] / "README.md"
posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions or symlinks")


def actions(console: str) -> dict[str, str]:
    """``{path: op}`` from an ``apply`` file list."""
    return {m.group(2): m.group(1) for ln in console.splitlines() if (m := ACTION.match(ln))}


def plan_entries(corpus: Path) -> list[dict]:
    return yaml.safe_load((corpus / ".sherpa" / "harness-plan.yaml").read_text(encoding="utf-8"))["entries"]


def proposed_unit(corpus: Path) -> tuple[str, str]:
    """``(target, scope)`` of the first proposed owner doc of a nested unit — the unit whose proximity file the
    theses on hand edits, covers and rollbacks use; BLOCKED when the plan proposes none."""
    for e in plan_entries(corpus):
        if e["kind"] == "owner-doc" and e["default"] == "propose" and e["scope"] and not e.get("decision"):
            if not e.get("covered"):  # a covered entry renders nothing — nothing to edit, reject or roll back
                return e["target"], e["scope"]
    pytest.skip("blocked: the plan proposes no owner doc for a nested unit")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------- first contact


@thesis(
    "T01", "doctor reports every prerequisite, a hint with its fix, no problem, exit 0", "README quick start, ADR-0018"
)
def test_t01_doctor_is_ready(sherpa: Sherpa, corpus: Path, ev):
    r = sherpa("doctor", "--offline", corpus)
    assert r.code == 0 and r.first == f"sherpa doctor — {sherpa.version}", r
    lines = r.lines[1:-1]
    names = [ln.split()[1] for ln in lines if ln.startswith(("  ✓ ", "  ! "))]
    assert names[:4] == ["python", "git", "install", "repository"] and "repositories" in names, r
    assert not any(ln.startswith("  ✗ ") for ln in lines), r
    for i, ln in enumerate(lines):  # a hint never stands without its fix
        if ln.startswith("  ! "):
            assert lines[i + 1].startswith("    hint: "), ln
            ev(ln.strip())
    assert ev(r.last).startswith(("ready — `sherpa plan` is the next step.", "0 problems, ")), r


# ---------------------------------------------------------------- scan


@thesis("T02", "scan is deterministic: same trunk rev → byte-identical model", "README § Determinism, ADR-0003")
def test_t02_scan_twice_gives_the_same_bytes(sherpa: Sherpa, corpus: Path, store: Store, ev):
    model = corpus / ".sherpa" / "codebase-model.json"
    r1 = sherpa("scan", corpus, "--no-fetch")
    assert r1.code == 0 and model.is_file(), r1
    first = model.read_bytes()
    r2 = sherpa("scan", corpus, "--no-fetch")
    assert r2.code == 0 and model.read_bytes() == first, "the second scan changed the model"
    store.data["model"] = first
    store.data["scan_line"] = r1.err.strip()
    ev(f"two scans, {len(first)} bytes each, identical")


@thesis("T04", "scan prints files, modules and its wall time in one summary line", "README § scanner")
def test_t04_scan_summary_line(store: Store, ev):
    line = store.need("scan_line", "T02")
    m = re.search(r"sherpa scan: .* — (\d+) files, .* (\d+) modules in (\d+\.\d) s → ", line)
    assert m, line
    assert int(m.group(1)) > 0 and int(m.group(2)) > 0 and float(m.group(3)) < 60, line
    ev(line)


@thesis("T03", "scan measures origin/<trunk>, never HEAD: a detached checkout gives the same model", "ADR-0003")
def test_t03_detached_head_same_model(sherpa: Sherpa, corpus: Path, store: Store, ev):
    first = store.need("model", "T02")
    branch = git(corpus, "rev-parse", "--abbrev-ref", "HEAD")
    git(corpus, "checkout", "-q", "HEAD~3")
    try:
        r = sherpa("scan", corpus, "--no-fetch")
    finally:
        git(corpus, "checkout", "-q", branch)
    assert r.code == 0, r
    assert (corpus / ".sherpa" / "codebase-model.json").read_bytes() == first, "the model followed HEAD"
    ev(f"detached at HEAD~3: model identical ({r.err.strip().split(' — ')[0]})")


# ---------------------------------------------------------------- plan


@thesis(
    "T05",
    "plan: proposals and reasoned no's with ✓/✗ checks; dormant and out-of-reach units listed",
    "README § planner, ADR-0006/0012/0014",
)
def test_t05_plan_proposals_and_reasoned_nos(planned: Run, ev):
    r = require(planned, "T05")
    head = re.match(r"harness-plan\.yaml — (\d+) proposals, (\d+) reasoned no's", r.first)
    assert head and int(head.group(1)) > 0 and int(head.group(2)) > 0, r
    entries = [ln for ln in r.lines if re.match(r"^  [+-] \S+ ", ln)]
    assert entries and entries[0].startswith("  + outcome "), r  # mandatory and first (ADR-0008)
    assert all(("✓" in ln or "✗" in ln) for ln in entries), [ln for ln in entries if "✓" not in ln and "✗" not in ln]
    notes = [ln for ln in r.lines if ln.startswith("  ") and not re.match(r"^  [+-] ", ln)]
    for note in notes:  # a dormant or small unit named in a note is listed above as a no, never dropped
        if m := re.match(r"  \d+ (?:dormant|small) units without owner doc .*?: (.+?) — ", note):
            named = re.sub(r", … \(\+\d+ more\)$", "", m.group(1)).split(", ")
            for name in named:
                assert any(ln.startswith("  - owner-doc") and f" {name} " in ln + " " for ln in entries), name
    ev(r.first)
    ev(next((n.strip() for n in notes if "dormant" in n), "no dormant units"))


@thesis("T06", "plan twice → byte-identical YAML; a --reject survives the re-plan", "ADR-0012")
def test_t06a_plan_twice_same_yaml(sherpa: Sherpa, corpus: Path, planned: Run, ev):
    require(planned, "T05")
    plan = corpus / ".sherpa" / "harness-plan.yaml"
    first = plan.read_bytes()
    r = sherpa("plan", corpus, "--no-fetch")
    assert r.code == 0 and plan.read_bytes() == first, r
    ev(f"two plans, {len(first)} bytes each, identical")


@thesis("T06", "plan twice → byte-identical YAML; a --reject survives the re-plan", "ADR-0012")
def test_t06b_reject_survives_a_replan(sherpa: Sherpa, corpus: Path, planned: Run, store: Store, ev):
    require(planned, "T05")
    proposed = [e for e in plan_entries(corpus) if e["kind"] in ("agent", "owner-doc") and e["default"] == "propose"]
    assert proposed, "the plan proposes neither an agent nor an owner doc"
    entry = min(proposed, key=lambda e: e["kind"] != "agent")  # an agent first: the owner docs stay for T11
    address = f"{entry['kind']}:{entry['target']}:{entry['scope']}"
    r1 = sherpa("plan", corpus, "--no-fetch", "--reject", address)
    assert r1.code == 0 and "(1 decided now" in r1.last, r1
    r2 = sherpa("plan", corpus, "--no-fetch")
    assert r2.code == 0 and "(1 decisions kept" in r2.last, r2
    row = next(ln for ln in r2.lines if re.match(rf"  \+ {entry['kind']}\s+{re.escape(entry['target'])}\s", ln))
    assert row.endswith(" [reject]"), row
    store.data["rejected"] = address
    ev(r1.last)
    ev(r2.last)


# ---------------------------------------------------------------- apply


@thesis("T07", "apply is dry run first: no terminal and no --yes writes nothing; --dry-run never writes", "ADR-0008")
def test_t07a_apply_without_terminal_writes_nothing(sherpa: Sherpa, corpus: Path, planned: Run, ev):
    require(planned, "T05")
    before = git_status(corpus)
    r = sherpa("apply", corpus)
    assert r.code == 0 and ev(r.last) == "dry run only — pass --yes to write (no terminal to ask).", r
    assert git_status(corpus) == before and not home_dirs(corpus)


@thesis("T07", "apply is dry run first: no terminal and no --yes writes nothing; --dry-run never writes", "ADR-0008")
def test_t07b_dry_run_lists_and_writes_nothing(sherpa: Sherpa, corpus: Path, planned: Run, ev):
    require(planned, "T05")
    before = git_status(corpus)
    r = sherpa("apply", "--dry-run", corpus)
    assert r.code == 0 and r.first.startswith("targets: ") and " · home: " in r.first, r
    listed = actions(r.out)
    assert listed and all(op in "+~" for op in listed.values()), listed  # ~ = a block appended into the team's file
    assert re.match(r"\d+ to add, \d+ to change, 0 unchanged, 0 skipped\.", r.last), r  # to change: appended
    assert git_status(corpus) == before and not home_dirs(corpus)
    ev(r.first)
    ev(r.last)


@thesis(
    "T08",
    "apply --yes writes the listed files, runs the checker, records harness_rev; check: 0 FAIL",
    "README, ADR-0013",
)
def test_t08_apply_writes(installed: Run, corpus: Path, ev):
    r = installed
    assert r.code == 0, r
    assert ev(r.line("check: ")).startswith("check: 0 FAIL"), r
    m = re.search(r"(\d+) files written · harness_rev ([0-9a-f]{12}) → \.sherpa/state\.json", ev(r.last))
    assert m and int(m.group(1)) > 0, r
    state = json.loads((corpus / ".sherpa" / "state.json").read_text(encoding="utf-8"))
    assert state["harness_rev"] == m.group(2)


@thesis(
    "E02",
    "apply writes only what the dry run listed: every new or changed path was announced, under home, .claude or .sherpa",
    "ADR-0013, files-and-exit-codes.md",
)
def test_e02_write_boundary(installed: Run, corpus: Path, store: Store, ev):
    require(installed, "T08")
    listed = actions(store.need("dry_run", "T08"))
    announced = {p for p, op in listed.items() if op in "+~"}
    on_disk = {ln[2:].strip().strip('"') for ln in git_status(corpus)}  # `?? x`, ` M x`, `!! x`
    strays = sorted(p for p in on_disk if p not in announced and not p.startswith(".sherpa/"))
    assert not strays, f"written but never listed: {strays}"
    missing = sorted(p for p in announced if not (corpus / p).is_file())
    assert not missing, f"listed but not on disk: {missing}"
    ev(f"{len(announced)} announced paths, {len(on_disk)} paths changed on disk, 0 strays")


@thesis("T10", "idempotent: the second apply --dry-run says nothing to do; status says drift: none", "README, ADR-0013")
def test_t10_second_apply_has_nothing_to_do(sherpa: Sherpa, corpus: Path, installed: Run, ev):
    require(installed, "T08")
    r = sherpa("apply", "--dry-run", corpus)
    assert r.code == 0 and ev(r.last) == "nothing to do.", r
    s = sherpa("status", corpus)
    assert s.code == 0 and ev(s.line("drift: ")) == "drift: none — files match the state and the plan", s
    assert s.line("plan: ") == "plan: current"


# ---------------------------------------------------------------- the written harness


@thesis("T14", "links resolve: check C4 clean in every file sherpa wrote, the root unit's included", "ADR-0047")
def test_t14_check_is_clean(sherpa: Sherpa, corpus: Path, installed: Run, ev):
    require(installed, "T08")
    r = sherpa("check", corpus)
    assert r.code == 0 and " 0 FAIL, " in ev(r.first), r
    if any(e["kind"] == "owner-doc" and e["default"] == "propose" and not e["scope"] for e in plan_entries(corpus)):
        root = (corpus / "AGENTS.md").read_text(encoding="utf-8")
        assert "../" not in root, "the root AGENTS.md links its owner doc with a ../ (F49)"
        ev("root unit: AGENTS.md links without ../")


@thesis(
    "E01",
    "the deployed checker runs standalone: a bare interpreter without site-packages, stdlib only, same verdict",
    "CLAUDE.md § Rules, ADR-0013",
)
def test_e01_deployed_checker_standalone(corpus: Path, installed: Run, ev):
    require(installed, "T08")
    home = installed.first.split("home: ")[1].strip() if "home: " in installed.first else ".agents"
    script = corpus / home / "scripts" / "sherpa-check.py"
    assert script.is_file(), f"no checker copy at {script}"
    r = subprocess.run(
        [sys.executable, "-I", "-S", str(script), str(corpus)],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "SHERPA_CHECK_STANDALONE": "1", "PYTHONUTF8": "1"},
        timeout=120,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Traceback" not in r.stderr and " 0 FAIL, " in r.stdout, r.stdout + r.stderr
    ev(f"python -I -S {script.relative_to(corpus).as_posix()}: {r.stdout.splitlines()[0].split(': ', 1)[1]}")


@thesis("T12", "the facts stamp carries the window end of the model, not today's date", "ADR-0019")
def test_t12_stamp_is_the_window_end(corpus: Path, installed: Run, ev):
    require(installed, "T08")
    as_of = json.loads((corpus / ".sherpa" / "codebase-model.json").read_text(encoding="utf-8"))["git"]["windows"][
        "as_of"
    ][:10]
    stamps = set()
    for p in list(corpus.glob(".agents/docs/modules/*.md")) + list(corpus.glob(".claude/docs/modules/*.md")):
        stamps.update(re.findall(r"as of (\d{4}-\d{2}-\d{2})", p.read_text(encoding="utf-8")))
    assert stamps == {as_of}, f"stamps {stamps} vs. model as_of {as_of}"
    today = dt.date.today().isoformat()
    ev(f"stamp as of {as_of}" + (" (today)" if as_of == today else f", today is {today}"))


@thesis(
    "T13",
    "proximity budgets: every nested AGENTS.md/CLAUDE.md sherpa wrote ≤ 8 KiB, the root ones ≤ 32 KiB",
    "ADR-0029",
)
def test_t13_budgets(sherpa: Sherpa, corpus: Path, installed: Run, store: Store, ev):
    require(installed, "T08")
    listed = actions(store.need("dry_run", "T08"))
    seeded = [p for p, op in listed.items() if op == "+" and Path(p).name in ("AGENTS.md", "CLAUDE.md")]
    appended = [p for p, op in listed.items() if op == "~" and Path(p).name in ("AGENTS.md", "CLAUDE.md")]
    assert seeded or appended
    for p in seeded:  # sherpa's whole: its budget (ADR-0029)
        size, budget = (corpus / p).stat().st_size, 32 * 1024 if "/" not in p else 8 * 1024
        assert size <= budget, f"{p}: {size} bytes over {budget}"
    over = [p for p in appended if (corpus / p).stat().st_size > 32 * 1024]  # the team's: the ceiling, as a C7 line
    if over:
        r = sherpa("check", corpus)
        for p in over:
            assert "ceiling 32 KiB" in r.line(p), r
    if seeded:
        largest = max(seeded, key=lambda p: (corpus / p).stat().st_size)
        ev(f"{len(seeded)} proximity files seeded, largest {largest} at {(corpus / largest).stat().st_size} bytes")
    if appended:
        ev(f"{len(appended)} team files appended to, {len(over)} over the runtime's ceiling — named by C7")


@thesis(
    "T11",
    "never overwrite: prose outside the markers survives; a hand edit inside a block is yours — reported, not rewritten",
    "ADR-0016/0030",
)
def test_t11a_prose_outside_the_markers_survives(sherpa: Sherpa, corpus: Path, installed: Run, ev):
    require(installed, "T08")
    _, scope = proposed_unit(corpus)
    f = corpus / scope / "AGENTS.md"
    assert f.is_file(), f
    original = f.read_bytes()
    f.write_bytes(original + b"\nTeam note - keep me.\n")
    try:
        r = sherpa("apply", "--dry-run", corpus)
        assert r.code == 0 and r.last == "nothing to do.", r
        assert f.read_bytes().endswith(b"Team note - keep me.\n")
        ev(f"a note appended after the block of {f.relative_to(corpus).as_posix()}: {r.last}")
    finally:
        f.write_bytes(original)


@thesis(
    "T11",
    "never overwrite: prose outside the markers survives; a hand edit inside a block is yours — reported, not rewritten",
    "ADR-0016/0030",
)
def test_t11b_hand_edit_inside_a_block_is_reported_not_rewritten(sherpa: Sherpa, corpus: Path, installed: Run, ev):
    require(installed, "T08")
    _, scope = proposed_unit(corpus)
    f = corpus / scope / "AGENTS.md"
    original = f.read_text(encoding="utf-8")
    begin, end = original.index("sherpa:begin"), original.index("sherpa:end")
    block = original[begin:end]
    edited = original[:begin] + block.replace("\n", "\n<!-- edited by the team -->\n", 1) + original[end:]
    f.write_text(edited, encoding="utf-8")
    try:
        s = sherpa("status", corpus)
        assert s.code == 0, s
        rel = f.relative_to(corpus).as_posix()
        assert ev(s.line(f"! {rel}")).endswith("hand-edited (skipped)"), s
        c = sherpa("check", corpus)
        assert (
            c.code == 0 and ev(c.line("C8")).startswith(f"  WARN C8 {rel}: block ") and "hand-edited" in c.line("C8")
        ), c
        assert f.read_text(encoding="utf-8") == edited, "status and check rewrote the file"
        r = sherpa("apply", "--dry-run", corpus)
        assert r.code == 0 and f.read_text(encoding="utf-8") == edited, "the dry run rewrote the file"
        assert "hand-edited" in ev(r.line(rel)), r
    finally:
        f.write_text(original, encoding="utf-8")


# ---------------------------------------------------------------- scripts and errors


@thesis(
    "T20",
    "--json on status, check and doctor parses; exit codes 0/1; errors on stderr as sherpa <cmd>: <msg> naming the fix",
    "files-and-exit-codes.md",
)
def test_t20a_json_reports_parse(sherpa: Sherpa, corpus: Path, installed: Run, ev):
    require(installed, "T08")
    keys = {"status": ("harness_rev", "drift", "findings"), "check": (), "doctor": ("checks", "problems")}
    for cmd, wanted in keys.items():
        r = sherpa(cmd, "--json", *(["--offline"] if cmd == "doctor" else []), corpus)
        assert r.code == 0, r
        data = json.loads(r.out)
        assert all(k in data for k in wanted), (cmd, data if isinstance(data, list) else sorted(data))
        ev(f"{cmd} --json: {type(data).__name__}, exit {r.code}")


@thesis(
    "T20",
    "--json on status, check and doctor parses; exit codes 0/1; errors on stderr as sherpa <cmd>: <msg> naming the fix",
    "files-and-exit-codes.md",
)
def test_t20b_error_on_stderr_names_the_fix(sherpa: Sherpa, tmp_path: Path, ev):
    r = sherpa("apply", "--yes", tmp_path)
    assert r.code == 1 and r.out == "", r
    line = r.err.strip().splitlines()[0]
    assert line.startswith("sherpa apply: ") and line.endswith("— run `sherpa plan` first"), r
    ev(line.replace(str(tmp_path), "<dir>"))
    u = sherpa("apply", "--frobnicate")
    assert u.code == 2 and "usage:" in u.err, u
    ev(f"unknown flag: exit {u.code}, usage on stderr")


# ---------------------------------------------------------------- adopt


@thesis("T15", "adopt rebuilds a lost state with the same harness_rev apply wrote", "README, ADR-0017")
def test_t15_adopt_rebuilds_a_lost_state(sherpa: Sherpa, corpus: Path, installed: Run, ev):
    require(installed, "T08")
    state = corpus / ".sherpa" / "state.json"
    rev = json.loads(state.read_text(encoding="utf-8"))["harness_rev"]
    state.unlink()
    r = sherpa("adopt", corpus)
    assert r.code == 0 and state.is_file(), r
    assert f"harness_rev {rev} → .sherpa/state.json" in ev(r.last), f"{r}\nwas {rev}"
    assert json.loads(state.read_text(encoding="utf-8"))["harness_rev"] == rev


@thesis("T16", "adopt never changes a byte of a hand-written harness file; lists it as a/?", "ADR-0007")
def test_t16_adopt_keeps_foreign_files(sherpa: Sherpa, corpus: Path, installed: Run, ev):
    require(installed, "T08")
    foreign = corpus / ".claude" / "agents" / "ops.md"
    # the deepest directory the test makes is the test's — `.claude/` itself on a repository without that target
    made = next((d for d in (corpus / ".claude", foreign.parent) if not d.is_dir()), None)
    foreign.parent.mkdir(parents=True, exist_ok=True)
    foreign.write_bytes(b"---\nname: ops\ndescription: mine\n---\n# ops\n")
    before = sha256(foreign)
    try:
        r = sherpa("adopt", corpus)
        assert r.code == 0, r
        line = ev(r.line(".claude/agents/ops.md"))
        assert line.strip().startswith(("a ", "? ")) and sha256(foreign) == before, r
    finally:
        rmtree(made or foreign)
        sherpa("adopt", corpus)  # drops the record of the file that is gone


# ---------------------------------------------------------------- one repository


@thesis(
    "T18",
    "one repository: a nested .git stops apply and adopt with the way out named; doctor says it first; dry runs go on with a note",
    "ADR-0045",
)
def test_t18_nested_repository(sherpa: Sherpa, corpus: Path, installed: Run, ev):
    require(installed, "T08")
    git(corpus, "init", "-q", "nested-tmp")
    try:
        d = sherpa("doctor", "--offline", corpus)
        assert d.code == 1 and "nested-tmp/" in ev(d.line("repositories")), d
        p = sherpa("apply", "--dry-run", corpus)
        assert p.code == 0 and "this preview goes on" in ev(p.line("note: nested-tmp/")), p
        a = sherpa("adopt", corpus)
        assert a.code == 1 and "move the clone out of the tree" in a.err, a
        ev(a.err.strip().splitlines()[0])
        assert not (corpus / ".sherpa" / "state.json.tmp").exists()
    finally:
        rmtree(corpus / "nested-tmp")


@thesis(
    "E08",
    "the WARN count apply prints after a write is the count check prints right after: drift is measured against the state this run wrote",
    "plan §13 F52",
)
def test_e08_apply_warn_count_equals_check(sherpa: Sherpa, corpus: Path, installed: Run, ev):
    require(installed, "T08")
    target, scope = proposed_unit(corpus)
    address = f"owner-doc:{target}:{scope}"
    require(sherpa("plan", corpus, "--no-fetch", "--reject", address), "T05")
    try:
        r = sherpa("apply", "--yes", corpus)
        assert r.code == 0, r
        m = re.match(r"check: (\d+) FAIL, (\d+) WARN$", ev(r.line("check: ")))
        assert m and "removed · harness_rev" in r.out, r
        c = sherpa("check", corpus)
        after = re.search(r": (\d+) FAIL, (\d+) WARN$", ev(c.first))
        assert after and (m.group(1), m.group(2)) == (after.group(1), after.group(2)), f"{r}\n{c}"
    finally:  # the harness the later theses expect: the entry back, its files written again
        require(sherpa("plan", corpus, "--no-fetch", "--accept", address), "T05")
        require(sherpa("apply", "--yes", corpus), "T08")


# ---------------------------------------------------------------- M3l: a revision that means something


@thesis(
    "E10",
    "harness_rev is over what an agent reads and the state carries tooling apart: the checker copy hand-edited moves tooling, not harness_rev",
    "ADR-0056",
)
def test_e10_harness_rev_is_content_only(sherpa: Sherpa, corpus: Path, installed: Run, ev):
    require(installed, "T08")
    state = json.loads((corpus / ".sherpa" / "state.json").read_text(encoding="utf-8"))
    rev, tooling = state["harness_rev"], state.get("tooling")
    assert re.fullmatch(r"[0-9a-f]{12}", rev) and re.fullmatch(r"[0-9a-f]{12}", tooling or "") and rev != tooling, state
    ev(f"state.json: harness_rev {rev} · tooling {tooling}")
    # ``adopt`` rebuilds both from the files; a changed checker copy (an older sherpa's) moves tooling only
    home = state["home"]
    checker = corpus / home / "scripts" / "sherpa-check.py"
    original = checker.read_bytes()
    try:
        checker.write_bytes(original.replace(b'SHERPA_VERSION = "', b'SHERPA_VERSION = "0.0.1-', 1))
        r = sherpa("adopt", "--dry-run", corpus)
        assert r.code == 0 and f"harness_rev {rev} " in r.last, r
        ev(f"checker copy changed → adopt --dry-run: {r.last}")
    finally:
        checker.write_bytes(original)


@thesis(
    "E11",
    "C7 on a proximity file the team wrote fires at the runtime's ceiling (32 KiB), not at sherpa's 8 KiB budget",
    "ADR-0029 amended, plan §14 F59",
)
def test_e11_c7_ceiling_for_the_teams_files(sherpa: Sherpa, corpus: Path, installed: Run, ev):
    require(installed, "T08")
    d = corpus / "tmp-team"
    f = d / "AGENTS.md"
    d.mkdir()
    try:
        f.write_text("# Team\n\n" + "The team's own guidance, line after line.\n" * 250, encoding="utf-8")  # ~11 KiB
        r = sherpa("check", corpus)
        assert r.code == 0 and "tmp-team/AGENTS.md" not in r.out, r
        ev(f"{f.stat().st_size} bytes, the team's: no C7 line in `sherpa check`")
        f.write_text("# Team\n\n" + "The team's own guidance, line after line.\n" * 800, encoding="utf-8")  # ~34 KiB
        r = sherpa("check", corpus)
        line = r.line("tmp-team/AGENTS.md")
        assert r.code == 0 and line.strip().startswith("WARN C7") and "ceiling 32 KiB" in line and "yours" in line, r
        ev(line)
    finally:
        rmtree(d)


@thesis(
    "E12",
    "a file git ignores is not the harness: check reports nothing in it, like adopt; tracked or unignored, it is checked",
    "plan §14 F62, ADR-0047",
)
def test_e12_git_ignored_files_are_not_checked(sherpa: Sherpa, corpus: Path, installed: Run, ev):
    require(installed, "T08")
    d = corpus / "tmp-vault"
    exclude = corpus / ".git" / "info" / "exclude"
    before = exclude.read_bytes() if exclude.is_file() else None
    d.mkdir()
    try:
        (d / "CLAUDE.md").write_text("# vault\n\n[dead](../nowhere.md)\n", encoding="utf-8")
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_bytes((before or b"") + b"\ntmp-vault/\n")
        r = sherpa("check", corpus)
        assert r.code == 0 and "tmp-vault/CLAUDE.md" not in r.out, r
        ev("tmp-vault/ ignored via .git/info/exclude: no finding in `sherpa check`")
        exclude.write_bytes(before or b"")
        r = sherpa("check", corpus)
        line = r.line("tmp-vault/CLAUDE.md")
        assert "C4 tmp-vault/CLAUDE.md: link target ../nowhere.md does not exist (yours)" in line, r
        ev(line)
    finally:
        rmtree(d)
        if before is None:
            exclude.unlink(missing_ok=True)
        else:
            exclude.write_bytes(before)


# ---------------------------------------------------------------- uninstall


@thesis(
    "T21",
    "apply --remove uninstalls: git status --short --ignored as before the first apply, no home directory left",
    "ADR-0048",
)
def test_t21_remove_leaves_the_corpus_clean(uninstalled: Run, corpus: Path, ev):
    r = uninstalled
    assert r.code == 0, r
    assert ev(r.line("uninstalled — ")).startswith("uninstalled — .sherpa/state.json"), r
    left = git_status(corpus)
    assert not left, f"left behind: {left}"
    assert not home_dirs(corpus), f"empty home directories left: {home_dirs(corpus)}"
    ev("git status --short --ignored: empty; no .agents/ or .claude/")


@thesis(
    "E09",
    "the uninstall names .sherpa/state.json once: in the uninstalled line, not in the summary line before it",
    "plan §13 F53",
)
def test_e09_uninstall_names_the_state_once(uninstalled: Run, ev):
    r = require(uninstalled, "T21")
    summary = ev(r.line(" · harness_rev "))
    assert "state.json" not in summary and re.search(r"harness_rev [0-9a-f]{12}$", summary), r
    assert ev(r.line("uninstalled — ")).startswith("uninstalled — .sherpa/state.json, "), r


# ---------------------------------------------------------------- from the clean corpus


@posix_only
@thesis(
    "T09",
    "a rollback is complete: a write error rolls back, exit 1, the corpus clean, no empty home left, the next apply not blocked",
    "ADR-0013/0032",
)
def test_t09_rollback_after_a_write_error(sherpa: Sherpa, clean_slate: Path, ev):
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root ignores directory permissions")
    corpus = clean_slate
    require(sherpa("plan", corpus, "--no-fetch"), "T05")
    _, scope = proposed_unit(corpus)
    unit = corpus / scope
    mode = unit.stat().st_mode
    unit.chmod(mode & ~0o222)
    try:
        r = sherpa("apply", "--yes", corpus)
    finally:
        unit.chmod(mode)
    assert r.code == 1 and ev(r.line("write failed: ")).endswith("— rolled back, nothing written"), r
    assert r.err.startswith("sherpa apply: write failed"), r
    left = [ln for ln in git_status(corpus) if ".sherpa/" not in ln]  # the plan and the model stay, nothing else
    assert not left and not home_dirs(corpus), f"after the rollback: {left} {home_dirs(corpus)}"
    n = sherpa("apply", "--dry-run", corpus)
    assert n.code == 0 and n.first.startswith("targets: ") and "note: both" not in n.out, n
    ev(f"next dry run: {n.first} — not blocked")


@thesis(
    "T17",
    "a nested AGENTS.md at a unit's path covers its owner-doc entry; apply appends the facts block and creates no skeleton",
    "ADR-0049",
)
def test_t17_own_agents_md_covers_the_entry(sherpa: Sherpa, clean_slate: Path, ev):
    corpus = clean_slate
    require(sherpa("plan", corpus, "--no-fetch"), "T05")
    target, scope = proposed_unit(corpus)
    own = corpus / scope / "AGENTS.md"
    if own.exists():
        pytest.skip("blocked: the unit already has an AGENTS.md of its own")
    own.write_text("# Notes\n\nOurs.\n", encoding="utf-8")
    p = sherpa("plan", corpus, "--no-fetch")
    assert p.code == 0 and f"[covered by {scope}/AGENTS.md]" in ev(p.line(f" {target} ")), p
    r = sherpa("apply", "--dry-run", corpus)
    assert r.code == 0, r
    listed = actions(r.out)
    assert listed.get(f"{scope}/AGENTS.md") == "~", listed
    skeletons = [x for x in listed if x.endswith(f"/docs/modules/{target}.md")]
    assert not skeletons, f"a skeleton next to the team's file: {skeletons}"
    ev(r.line(f"{scope}/AGENTS.md"))


@thesis(
    "T19",
    "both homes present and nothing decides: dry runs assume .agents and say so; a write without a terminal refuses naming the fix",
    "ADR-0036",
)
def test_t19_two_empty_homes(sherpa: Sherpa, clean_slate: Path, ev):
    corpus = clean_slate
    require(sherpa("plan", corpus, "--no-fetch"), "T05")
    (corpus / ".agents").mkdir()
    (corpus / ".claude").mkdir()
    d = sherpa("apply", "--dry-run", corpus)
    assert d.code == 0 and d.first.endswith("home: .agents"), d
    assert ev(d.line("note: both .agents/ and .claude/ exist")).endswith('or ".claude" in sherpa.toml.'), d
    w = sherpa("apply", "--yes", corpus)
    assert w.code == 1 and w.out == "", w
    line = w.err.strip().splitlines()[0]
    assert line.startswith("sherpa apply: both .agents/ and .claude/ exist") and "sherpa.toml" in line, w
    ev(line)
    assert home_dirs(corpus) == [".agents", ".claude"] and not any((corpus / ".agents").iterdir())


@thesis(
    "E03",
    "sherpa.toml [apply] home = .claude decides the home: doctor names it, the dry run lists the core under .claude and nothing under .agents",
    "ADR-0015/0036",
)
def test_e03_configured_home(sherpa: Sherpa, clean_slate: Path, ev):
    corpus = clean_slate
    (corpus / "sherpa.toml").write_text('[apply]\nhome = ".claude"\n', encoding="utf-8")
    require(sherpa("plan", corpus, "--no-fetch"), "T05")
    d = sherpa("doctor", "--offline", corpus)
    assert d.code == 0 and ev(d.line("layout")).endswith("home .claude (sherpa.toml)"), d
    r = sherpa("apply", "--dry-run", corpus)
    assert r.code == 0 and ev(r.first).endswith("home: .claude"), r
    listed = actions(r.out)
    assert ".claude/scripts/sherpa-check.py" in listed and any(p.startswith(".claude/docs/modules/") for p in listed)
    assert not any(p.startswith(".agents/") for p in listed), sorted(listed)


@thesis(
    "E04",
    "an existing CRLF file keeps its line endings through the append and comes back byte for byte after the uninstall",
    "ADR-0016, ADR-0048",
)
def test_e04_crlf_file_keeps_its_line_endings(sherpa: Sherpa, clean_slate: Path, ev):
    corpus = clean_slate
    f = corpus / "CLAUDE.md"
    if f.exists():
        pytest.skip("blocked: the corpus has a CLAUDE.md of its own")
    original = b"# Project\r\n\r\nHand-written.\r\n"
    f.write_bytes(original)
    require(sherpa("plan", corpus, "--no-fetch"), "T05")
    a = sherpa("apply", "--yes", corpus)
    assert a.code == 0, a
    text = f.read_bytes()
    assert text.startswith(original) and b"sherpa:begin" in text, text[:200]
    crlf, lf = text.count(b"\r\n"), text.count(b"\n")
    assert crlf == lf, f"sherpa introduced {lf - crlf} bare LF"
    ev(f"CLAUDE.md after apply: {crlf} lines, all CRLF")
    r = sherpa("apply", "--remove", "--yes", corpus)
    assert r.code == 0 and f.read_bytes() == original, r
    ev("after --remove: byte-identical")


@posix_only
@thesis(
    "E05",
    "a harness file that is a dangling symlink is a C4 finding, not a traceback, and apply never writes through it",
    "ADR-0031, ADR-0047, plan §13 F51",
)
def test_e05_dangling_symlink_is_a_finding(sherpa: Sherpa, clean_slate: Path, ev):
    corpus = clean_slate
    require(sherpa("plan", corpus, "--no-fetch"), "T05")
    _, scope = proposed_unit(corpus)
    link = corpus / scope / "AGENTS.md"
    if link.exists():
        pytest.skip("blocked: the unit already has an AGENTS.md of its own")
    link.symlink_to("nowhere.md")
    c = sherpa("check", corpus)
    assert c.code == 1 and "Traceback" not in c.err, c
    assert (
        ev(c.line(f"{scope}/AGENTS.md")).strip()
        == f"FAIL C4 {scope}/AGENTS.md: symlink target nowhere.md does not exist"
    ), c
    r = sherpa("apply", "--dry-run", corpus)
    assert r.code == 0 and "Traceback" not in r.err, r
    assert "symlink in the path — never written through (skipped)" in ev(r.line(f"! {scope}/AGENTS.md")), r
    assert link.is_symlink() and not link.exists()


def rename_unit(corpus: Path, target: str, scope: str) -> str | None:
    """Rename the unit in its manifest: the first quoted ``target`` in a manifest file of ``scope`` becomes
    ``<target>2``; None when no manifest there carries the name (an ecosystem that names units by directory)."""
    unit = corpus / scope
    for manifest in sorted(p for p in unit.iterdir() if p.is_file() and p.suffix in (".toml", ".json", ".mod", ".xml")):
        text = manifest.read_text(encoding="utf-8", errors="replace")
        new, n = re.subn(rf"([\"'])({re.escape(target)})\1", rf"\g<1>{target}2\g<1>", text, count=1)
        if n:
            manifest.write_text(new, encoding="utf-8")
            return f"{target}2"
    return None


class TrunkMove:
    """A commit on the local trunk and the remote-tracking ref moved onto it — the trunk moved as far as
    ``scan`` is concerned (ADR-0003), without a push; ``restore`` puts both back, whatever the thesis did."""

    def __init__(self, corpus: Path) -> None:
        self.corpus = corpus
        model = json.loads((corpus / ".sherpa" / "codebase-model.json").read_text(encoding="utf-8"))
        self.ref = model["git"]["trunk"]["ref"]  # origin/main
        self.head, self.trunk = git(corpus, "rev-parse", "HEAD"), git(corpus, "rev-parse", self.ref)

    def commit(self, message: str) -> None:
        git(self.corpus, "add", "-A")
        git(self.corpus, "commit", "-q", "-m", message)
        git(self.corpus, "update-ref", f"refs/remotes/{self.ref}", "HEAD")

    def restore(self) -> None:
        git(self.corpus, "update-ref", f"refs/remotes/{self.ref}", self.trunk)
        git(self.corpus, "reset", "-q", "--hard", self.head)


@thesis(
    "E06",
    "a rejection follows a unit whose manifest name changes and whose path stays; the re-plan says so once and keeps it by key from then on",
    "plan §13 F55",
)
def test_e06_decision_follows_a_renamed_unit(sherpa: Sherpa, clean_slate: Path, ev):
    corpus = clean_slate
    require(sherpa("plan", corpus, "--no-fetch"), "T05")
    agents = [e for e in plan_entries(corpus) if e["kind"] == "agent" and e["default"] == "propose" and e["scope"]]
    if not agents:
        pytest.skip("blocked: the plan proposes no agent for a nested unit")
    target, scope = agents[0]["target"], agents[0]["scope"]
    r0 = sherpa("plan", corpus, "--no-fetch", "--reject", f"agent:{target}:{scope}")
    assert r0.code == 0 and "(1 decided now" in r0.last, r0
    move = TrunkMove(corpus)
    try:
        renamed = rename_unit(corpus, target, scope)
        if renamed is None:
            pytest.skip(f"blocked: no manifest in {scope} carries the unit's name")
        move.commit(f"rename {target} to {renamed}")
        r = sherpa("plan", corpus, "--no-fetch")
        assert r.code == 0 and "rescanning" in r.err, r
        line = ev(r.line("followed from"))
        assert (
            line.strip()
            == f"agent:{renamed}:{scope} [reject] — followed from agent:{target}:{scope} (same path, renamed)"
        )
        assert "(1 decisions kept" in ev(r.last), r
        entry = next(e for e in plan_entries(corpus) if e["kind"] == "agent" and e["scope"] == scope)
        assert entry["target"] == renamed and entry["decision"] == "reject", entry
        again = sherpa("plan", corpus, "--no-fetch")
        assert again.code == 0 and "followed from" not in again.out and "(1 decisions kept" in again.last, again
    finally:
        move.restore()


@thesis(
    "E07",
    "a decision on an entry that left the plan is dropped with one line naming it, and the new plan carries no trace of it",
    "plan §13 F42",
)
def test_e07_dropped_decision_is_named_once(sherpa: Sherpa, clean_slate: Path, ev):
    corpus = clean_slate
    require(sherpa("plan", corpus, "--no-fetch"), "T05")
    target, scope = proposed_unit(corpus)
    address = f"owner-doc:{target}:{scope}"
    r0 = sherpa("plan", corpus, "--no-fetch", "--reject", address)
    assert r0.code == 0 and "(1 decided now" in r0.last, r0
    move = TrunkMove(corpus)
    try:
        git(corpus, "rm", "-rq", scope)
        move.commit(f"remove {scope}")
        r = sherpa("plan", corpus, "--no-fetch")
        assert r.code == 0 and "rescanning" in r.err, r
        assert ev(r.line("— dropped")).strip() == f"{address} [reject] is no longer in the plan — dropped", r
        assert r.out.count("— dropped") == 1 and "decisions kept" not in r.last, r
        assert not any(e["decision"] for e in plan_entries(corpus)), "the dropped decision is still in the YAML"
    finally:
        move.restore()


# ---------------------------------------------------------------- the README


@thesis("T22", "README numbers are true: the test count it prints is the count pytest collects", "CLAUDE.md § README")
def test_t22_readme_test_count(ev):
    m = re.search(r"# (\d+) tests, ~(\d+) % coverage", README.read_text(encoding="utf-8"))
    assert m, "README names no test count"
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        cwd=README.parent,
        timeout=300,
    )
    tail = r.stdout.strip().splitlines()[-1]
    n = re.match(r"(\d+) tests? collected", tail)
    assert n, tail
    assert int(n.group(1)) == int(m.group(1)), f"README says {m.group(1)} tests, pytest collects {n.group(1)}"
    ev(f"README: {m.group(1)} tests · collected: {n.group(1)}")
