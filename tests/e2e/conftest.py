"""The end-to-end theses of README, CLAUDE.md and the ADR index, run against the ``sherpa`` command as a user
runs it (a subprocess, never an import), on one corpus repository, in the order of the lifecycle
doctor → scan → plan → apply → status/check → adopt → apply --remove (ADR-0055).

Not part of ``pytest -q`` (``--ignore=tests/e2e`` in pyproject): ``pytest tests/e2e -q`` runs them, CI runs
them as a job of their own. The corpus is the built-in monorepo from ``corpus.py`` unless ``SHERPA_E2E_REPO``
names a local clone — then that repository is measured and left as found; its path never appears in a file of
this repository (CLAUDE.md § Product, not project).

Three fixtures carry the lifecycle — ``planned``, ``installed``, ``uninstalled`` — each runs its command once
per session and keeps the result; a thesis that needs a phase asks for it, and when the phase's command failed
the thesis is BLOCKED (skipped with the failing line), not red for a reason that is not its own. Every thesis
records the output line that proves it (``ev``), and the session ends with the theses table.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from tests.conftest import ENV as GIT_ENV
from tests.e2e.corpus import build_corpus

TIMEOUT = 600  # seconds per command — a real corpus has 20k files; the built-in one takes well under a second


@dataclass(frozen=True)
class Run:
    """One invocation of ``sherpa``: what a user would see."""

    args: tuple[str, ...]
    code: int
    out: str
    err: str

    @property
    def lines(self) -> list[str]:
        return [ln for ln in self.out.splitlines() if ln.strip()]

    @property
    def last(self) -> str:
        return self.lines[-1] if self.lines else ""

    @property
    def first(self) -> str:
        return self.lines[0] if self.lines else ""

    def line(self, needle: str) -> str:
        """The first stdout line containing ``needle`` — the evidence a thesis cites; fails with the whole
        output when there is none, so a FAIL shows what sherpa said instead."""
        for ln in self.out.splitlines():
            if needle in ln:
                return ln
        raise AssertionError(f"no line with {needle!r} in `sherpa {' '.join(self.args)}`:\n{self.out}{self.err}")

    def __str__(self) -> str:
        return f"`sherpa {' '.join(self.args)}` exit {self.code}\n{self.out}{self.err}"


class Sherpa:
    """Runs the ``sherpa`` console script of this interpreter — the product, not the package — with the
    environment of a CI job: no update check, no terminal on stdin, UTF-8 on every platform."""

    def __init__(self, cache: Path) -> None:
        script = shutil.which("sherpa", path=str(Path(sys.executable).parent))
        self.argv0 = (
            [script] if script else [sys.executable, "-c", "from sherpa.cli import main; raise SystemExit(main())"]
        )
        from sherpa import __version__

        self.version = __version__
        self.env = {
            **os.environ,
            "SHERPA_NO_UPDATE_CHECK": "1",
            "SHERPA_CACHE_DIR": str(cache),
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
        }

    def __call__(self, *args: str | Path, cwd: Path | None = None) -> Run:
        argv = [str(a) for a in args]
        r = subprocess.run(
            [*self.argv0, *argv],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env=self.env,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            timeout=TIMEOUT,
        )
        return Run(tuple(argv), r.returncode, r.stdout, r.stderr)


def git(repo: Path, *args: str) -> str:
    """Git in the corpus with the fixture identity — the external corpus is never committed to, so the
    identity only matters for the built-in one and for ``git init`` in T18."""
    r = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, **GIT_ENV},
        check=True,
    )
    return r.stdout.strip()


def git_status(repo: Path) -> list[str]:
    """``git status --short --ignored --untracked-files=all`` — every path sherpa could have touched, one per
    line; empty is the only acceptable state before the first thesis and after the last."""
    out = git(repo, "status", "--short", "--ignored", "--untracked-files=all")
    return [ln for ln in out.splitlines() if ln.strip()]


def rmtree(path: Path) -> None:
    """Remove a tree that may hold read-only files (a ``.git`` on Windows, a directory T09 made unwritable)."""

    def _writable(fn, p, _exc):
        os.chmod(p, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
        fn(p)

    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path, onexc=_writable)


def home_dirs(repo: Path) -> list[str]:
    """The harness home directories present at the root — git does not show an empty one, so the theses on a
    complete rollback and a complete uninstall look themselves (ADR-0032 amended)."""
    return sorted(h for h in (".agents", ".claude") if (repo / h).is_dir())


LEFTOVERS = (".sherpa", ".agents", ".claude", "nested-tmp", "sherpa.toml")


def scrub(repo: Path, *extra: Path) -> None:
    """What a thesis may leave behind when it fails half-way: sherpa's directories, the files a thesis wrote
    at the root, then git takes back every tracked change and every untracked file. Never touches ignored
    files beyond sherpa's own — an external corpus was verified clean before the run, so nothing else is there."""
    for rel in LEFTOVERS:
        rmtree(repo / rel)
    for p in extra:
        rmtree(p)
    git(repo, "checkout", "-q", "--", ".")
    git(repo, "clean", "-qfd")


# ---------------------------------------------------------------- the corpus and the runner


@dataclass
class Store:
    """What one thesis hands to the next: the model bytes T02 keeps for T03, the plan's console for T06, the
    files ``apply`` listed for the write-boundary thesis. Session-wide, filled in lifecycle order."""

    data: dict[str, object] = field(default_factory=dict)
    evidence: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def need(self, key: str, thesis: str):
        """The value an earlier thesis stored, or BLOCKED naming it — a thesis run alone (``-k``) says what it
        needs instead of failing on a missing key."""
        if key not in self.data:
            pytest.skip(f"blocked: needs {key} from {thesis}")
        return self.data[key]


STORE = pytest.StashKey[Store]()


@pytest.fixture(scope="session")
def store(request: pytest.FixtureRequest) -> Store:
    s = Store()
    request.config.stash[STORE] = s
    return s


@pytest.fixture(scope="session")
def external() -> Path | None:
    """The corpus named by ``SHERPA_E2E_REPO``, or None for the built-in one."""
    p = os.environ.get("SHERPA_E2E_REPO")
    return Path(p).resolve() if p else None


@pytest.fixture(scope="session")
def corpus(tmp_path_factory: pytest.TempPathFactory, external: Path | None, store: Store):
    """The repository under test. External: must be a clone with an ``origin`` and be clean including ignored
    files — a dirty corpus stops the run before the first thesis, because the last thesis is that the run left
    nothing behind; fetched once, so every ``scan`` and ``plan`` below runs with ``--no-fetch`` and the trunk
    does not move under the test (ADR-0003). At the end the harness is taken back and the corpus is verified
    clean again — that verification is the cleanup contract of the e2e-tester agent."""
    if external is None:
        repo = build_corpus(tmp_path_factory.mktemp("corpus", numbered=False))
        store.data["corpus_kind"] = "built-in"
        yield repo
        return
    if not (external / ".git").exists():
        pytest.exit(f"SHERPA_E2E_REPO: {external} is not a git repository", returncode=2)
    if dirty := git_status(external):
        pytest.exit(f"SHERPA_E2E_REPO: the corpus is not clean — {len(dirty)} paths in `git status --ignored`", 2)
    git(external, "fetch", "origin", "-q")
    store.data["corpus_kind"] = "external"
    try:
        yield external
    finally:
        sherpa = Sherpa(tmp_path_factory.mktemp("cache"))
        if (external / ".sherpa" / "state.json").exists():
            sherpa("apply", "--remove", "--yes", external)
        scrub(external)
        left = git_status(external)
        assert not left and not home_dirs(external), f"the corpus is not clean after the run: {left}"


@pytest.fixture(scope="session")
def sherpa(tmp_path_factory: pytest.TempPathFactory) -> Sherpa:
    return Sherpa(tmp_path_factory.mktemp("cache"))


# ---------------------------------------------------------------- the lifecycle phases


def require(run: Run, thesis: str) -> Run:
    """A phase that failed blocks the theses behind it — they skip naming the phase, so the table shows one
    FAIL where the product broke and BLOCKED where nothing could be measured."""
    if run.code != 0:
        pytest.skip(
            f"blocked by {thesis}: `sherpa {' '.join(run.args)}` exit {run.code} — {run.last or run.err.strip()}"
        )
    return run


@pytest.fixture(scope="session")
def planned(sherpa: Sherpa, corpus: Path, store: Store) -> Run:
    """The first ``sherpa plan`` of the session (T05); the plan on disk afterwards is what ``apply`` reads."""
    run = sherpa("plan", corpus, "--no-fetch")
    store.data["plan_console"] = run.out
    return run


@pytest.fixture(scope="session")
def installed(sherpa: Sherpa, corpus: Path, planned: Run, store: Store) -> Run:
    """The first ``sherpa apply --yes`` of the session (T08), preceded by the dry run whose file list the
    write-boundary thesis compares with what appeared on disk."""
    require(planned, "T05")
    store.data["dry_run"] = sherpa("apply", "--dry-run", corpus).out
    run = sherpa("apply", "--yes", corpus)
    store.data["apply"] = run
    return run


@pytest.fixture(scope="session")
def uninstalled(sherpa: Sherpa, corpus: Path, installed: Run, store: Store) -> Run:
    """``sherpa apply --remove --yes`` after every thesis on the installed harness ran (T21)."""
    require(installed, "T08")
    run = sherpa("apply", "--remove", "--yes", corpus)
    store.data["remove"] = run
    return run


@pytest.fixture
def clean_slate(corpus: Path, uninstalled: Run, store: Store):
    """A thesis that starts from the uninstalled corpus (T09, T17, T19 and the follow-ups): it may write what
    it needs, and afterwards every leftover goes and the corpus must be clean again — whatever the thesis did."""
    require(uninstalled, "T21")
    if left := git_status(corpus):
        pytest.skip(f"blocked: the corpus is not clean before this thesis — {left[:3]}")
    yield corpus
    scrub(corpus)
    assert not git_status(corpus) and not home_dirs(corpus), "the thesis left something behind"


# ---------------------------------------------------------------- evidence and the theses table


@pytest.fixture
def ev(request: pytest.FixtureRequest, store: Store, corpus: Path):
    """``ev(line)`` records the output line that proves the thesis of the current test (its ``thesis`` marker)
    and returns it, so an assertion and its evidence are the same line. The corpus path reads ``<corpus>`` in
    the table — the report never names the repository (the e2e-tester's first invariant)."""
    marker = request.node.get_closest_marker("thesis")
    thesis = marker.args[0] if marker else request.node.name

    def record(line: str) -> str:
        store.evidence[thesis].append(line.strip().replace(str(corpus), "<corpus>").replace(corpus.name, "<corpus>"))
        return line

    return record


OUTCOME = pytest.StashKey[dict[str, str]]()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """PASS, FAIL, BLOCKED (skipped because an earlier phase failed), SKIP (this platform) or ERROR per test."""
    outcome = yield
    report: pytest.TestReport = outcome.get_result()
    if report.when == "call" or (report.when == "setup" and not report.passed):
        reason = str(report.longrepr[2]) if report.skipped and isinstance(report.longrepr, tuple) else ""
        if report.passed:
            result = "PASS"
        elif report.failed:
            result = "FAIL" if report.when == "call" else "ERROR"
        else:
            result = "BLOCKED" if reason.startswith("Skipped: blocked") else "SKIP"
        item.config.stash.setdefault(OUTCOME, {})[item.nodeid] = result


def pytest_terminal_summary(terminalreporter, exitstatus: int, config: pytest.Config) -> None:
    """The theses table the e2e-tester agent reports: id · claim · source · result · evidence. One row per
    thesis; a thesis with several tests shows the worst result and every evidence line."""
    store = config.stash.get(STORE, None)
    outcomes = config.stash.get(OUTCOME, {})
    if store is None or not outcomes:
        return
    rows: dict[str, dict[str, object]] = {}
    for item in getattr(config, "_e2e_items", []):
        marker = item.get_closest_marker("thesis")
        if marker is None:
            continue
        tid, claim, source = marker.args
        row = rows.setdefault(tid, {"claim": claim, "source": source, "results": []})
        row["results"].append(outcomes.get(item.nodeid, "-"))  # type: ignore[union-attr]
    rank = {"FAIL": 0, "BLOCKED": 1, "SKIP": 2, "-": 3, "PASS": 4}
    tr = terminalreporter
    tr.section(f"e2e theses — corpus: {store.data.get('corpus_kind', '?')}")
    for tid in rows:  # file order — the lifecycle's order
        row = rows[tid]
        worst = min(row["results"], key=lambda r: rank[r])  # type: ignore[arg-type]
        if worst == "-":
            continue  # deselected (-k): not run, not reported
        tr.write_line(f"{tid}  {worst:<7} {row['claim']}  [{row['source']}]")
        for line in store.evidence.get(tid, []):
            tr.write_line(f"      {line}")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    config._e2e_items = list(items)  # type: ignore[attr-defined]
