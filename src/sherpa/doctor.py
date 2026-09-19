"""``sherpa doctor`` — every prerequisite as one line with a fix; the first command a new user runs.

Levels: ``ok`` (✓), ``warn`` (!) for things sherpa works without but the user should know, ``fail`` (✗) for what
blocks a command — ``scan`` (python, git, repository, origin, trunk) or ``apply`` and ``adopt`` (a nested
repository, ADR-0045). Exit 1 only on a fail. Checks are pure functions over the environment so tests can run them one
by one; the update check is the only network access and honours ``SHERPA_NO_UPDATE_CHECK``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from sherpa import __version__, config, gitinfo, update

MIN_PYTHON = (3, 12)
MIN_GIT = (2, 20)  # `git check-ignore --stdin -z` and `symbolic-ref --quiet` as used by the scanner


@dataclass(frozen=True)
class Check:
    name: str
    level: str  # "ok" | "warn" | "fail"
    detail: str
    fix: str = ""


def check_python() -> Check:
    v = sys.version_info[:3]
    detail = f"{'.'.join(map(str, v))} at {sys.executable}"
    if v[:2] < MIN_PYTHON:
        return Check("python", "fail", detail, f"Python ≥ {'.'.join(map(str, MIN_PYTHON))} is required")
    return Check("python", "ok", detail)


def check_git() -> Check:
    git = shutil.which("git")
    if not git:
        return Check("git", "fail", "not on PATH", "install git (https://git-scm.com) and open a new shell")
    try:
        out = subprocess.run([git, "--version"], capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return Check("git", "fail", f"{git}: {e}", "reinstall git")
    version = update.parse_version(out.split()[-1].split(".windows")[0]) if out else (0,)
    if version < MIN_GIT:
        return Check("git", "warn", out, f"git ≥ {'.'.join(map(str, MIN_GIT))} recommended")
    return Check("git", "ok", f"{out} ({git})")


def check_repo(repo: Path) -> Check:
    if not gitinfo.is_repo(repo):
        return Check("repository", "fail", f"{repo} is not a git repository", "cd into the repository or `git init`")
    return Check("repository", "ok", str(repo))


def check_origin(repo: Path) -> Check:
    if not gitinfo.has_remote(repo):
        return Check(
            "origin", "fail", "no remote named origin", "`git remote add origin <url>` — sherpa measures origin/<trunk>"
        )
    return Check("origin", "ok", gitinfo.origin_url(repo))


def check_trunk(repo: Path, override: str | None) -> Check:
    try:
        t = gitinfo.resolve_trunk(repo, override)
    except gitinfo.GitError as e:
        msg = str(e)
        fix = msg.split("Fix: ", 1)[1] if "Fix: " in msg else "`git fetch origin` and set `trunk` in sherpa.toml"
        return Check("trunk", "fail", msg.split(". Fix:")[0], fix)
    if t.source == "candidate":
        return Check(
            "trunk",
            "warn",
            f"{t.ref} @ {t.rev[:10]} (guessed from candidates)",
            "`git remote set-head origin -a` or `trunk` in sherpa.toml [scan] makes it explicit",
        )
    return Check("trunk", "ok", f"{t.ref} @ {t.rev[:10]} ({t.source})")


def check_config(repo: Path) -> tuple[Check, str | None]:
    """Returns the check and the trunk override for check_trunk."""
    p = repo / config.CONFIG_NAME
    if not p.exists():
        return Check("sherpa.toml", "ok", "absent — defaults apply"), None
    try:
        cfg = config.load(repo)
    except (ValueError, OSError) as e:
        return Check("sherpa.toml", "fail", str(e), f"fix the key in {p}"), None
    return Check("sherpa.toml", "ok", str(p)), cfg.scan.trunk


def check_runtime(repo: Path) -> Check:
    """Which agent runtime is visible and which targets ``apply`` will render for it (``sherpa.toml``, then the
    state, then the repository's files, ADR-0015). Claude Code on the ``PATH`` without ``claude`` among the targets
    is a hint: the outcome hook would not be installed (ADR-0008) — a root ``AGENTS.md`` alone selects
    ``agents-md`` only. Informational otherwise; sherpa works without a runtime."""
    from sherpa.apply import state as state_mod

    found = []
    if shutil.which("claude"):
        found.append("claude (Claude Code CLI)")
    if (repo / ".claude").is_dir() or (repo / "CLAUDE.md").is_file():
        found.append(".claude/ or CLAUDE.md in the repo")
    if (repo / ".agents").is_dir() or (repo / "AGENTS.md").is_file():
        found.append(".agents/ or AGENTS.md in the repo")
    for tool in ("codex", "cursor", "gemini"):
        if shutil.which(tool):
            found.append(f"{tool} on PATH")
    if not found:
        return Check(
            "runtime",
            "warn",
            "no agent runtime detected",
            "sherpa still writes the harness (AGENTS.md family + .claude); "
            "install Claude Code, Codex or Cursor to use it",
        )
    cfg = config.load(repo).apply
    try:
        state_targets = (
            state_mod.load(repo / state_mod.STATE_PATH).targets if (repo / state_mod.STATE_PATH).is_file() else ()
        )
    except ValueError:
        state_targets = ()
    targets = tuple(cfg.targets or state_targets or config.detect_targets(repo))
    detail = f"{', '.join(found)} → targets: {', '.join(targets)}"
    if shutil.which("claude") and "claude" not in targets:
        return Check(
            "runtime",
            "warn",
            detail,
            'Claude Code is here but not a target — `[apply] targets = ["claude", "agents-md"]` in sherpa.toml, '
            "or `.claude/` in the repo; without it no outcome hook is installed (ADR-0008)",
        )
    return Check("runtime", "ok", detail)


def check_layout(repo: Path) -> Check:
    """Where the core will live: ``sherpa.toml``, then the state, then the directories. Both homes and nothing
    decided is the one case ``apply --yes`` and ``adopt`` refuse (ADR-0036) — named here before it bites."""
    from sherpa.apply import state as state_mod

    cfg = config.load(repo).apply
    if cfg.home:
        return Check("layout", "ok", f"home {cfg.home} (sherpa.toml)")
    try:
        state_home = state_mod.load(repo / state_mod.STATE_PATH).home if (repo / state_mod.STATE_PATH).is_file() else ""
    except ValueError:
        state_home = ""
    if state_home:
        return Check("layout", "ok", f"home {state_home} (state)")
    both = (repo / ".agents").is_dir() and (repo / ".claude").is_dir()
    if both:
        return Check(
            "layout",
            "warn",
            "both .agents/ and .claude/ exist and nothing decides where the core lives",
            '`[apply] home = ".agents"` or `".claude"` in sherpa.toml — `apply` asks on a terminal, refuses with --yes',
        )
    home = ".claude" if (repo / ".claude").is_dir() else ".agents"
    return Check("layout", "ok", f"home {home} ({'found' if (repo / home).is_dir() else 'default'})")


def check_nested(repo: Path) -> Check:
    """Sherpa works with one repository (ADR-0045): a nested one anywhere in the tree stops ``apply`` and ``adopt``."""
    nested = gitinfo.nested_repositories(repo)
    if not nested:
        return Check("repositories", "ok", "one — no nested repository in the tree")
    shown = ", ".join(f"{d}/" for d in nested[:5]) + (f" and {len(nested) - 5} more" if len(nested) > 5 else "")
    what = "is a repository of its own" if len(nested) == 1 else "are repositories of their own"
    return Check(
        "repositories",
        "fail",
        f"{shown} {what} ({nested[0]}/.git) — `apply` and `adopt` refuse, sherpa works with one repository",
        "move the clone out of the tree, or run sherpa in that repository",
    )


def check_installer() -> Check:
    kind = update.installer()
    if kind == "editable":
        return Check("install", "ok", f"sherpa {__version__}, editable clone — `git pull` updates it")
    tool = shutil.which(kind) if kind in ("uv", "pipx") else sys.executable
    if kind in ("uv", "pipx") and not tool:
        return Check(
            "install", "warn", f"sherpa {__version__} via {kind}, but {kind} is not on PATH", f"reinstall {kind}"
        )
    return Check("install", "ok", f"sherpa {__version__} via {kind} ({tool})")


def check_update() -> Check:
    if os.environ.get(update.NO_CHECK_ENV):
        return Check("update", "ok", f"check disabled ({update.NO_CHECK_ENV})")
    tok = update.token()
    try:
        rel = update.latest_release(tok)
    except update.UpdateError as e:
        return Check("update", "warn", str(e), "`gh auth login`, GITHUB_TOKEN or git credentials for the repository")
    if update.is_newer(rel.version):
        return Check("update", "warn", f"{rel.version} available, you have {__version__}", "`sherpa self-update`")
    via = "PyPI" if rel.index == "pypi" else ("the GitHub API" if tok else "git ls-remote")
    return Check("update", "ok", f"{__version__} is current (via {via})")


def run(repo: Path, *, network: bool = True) -> list[Check]:
    checks = [check_python(), check_git(), check_installer()]
    if checks[1].level == "fail":
        return checks + [Check("repository", "fail", "skipped — git missing", "")]
    r = check_repo(repo)
    checks.append(r)
    if r.level == "ok":
        checks.append(check_origin(repo))
        cfg, trunk = check_config(repo)
        checks.append(cfg)
        checks.append(check_trunk(repo, trunk))
        checks.append(check_runtime(repo))
        checks.append(check_layout(repo))
        checks.append(check_nested(repo))
    if network:
        checks.append(check_update())
    return checks


MARK = {"ok": "✓", "warn": "!", "fail": "✗"}


def render(checks: list[Check]) -> str:
    lines = [f"sherpa doctor — {__version__}"]
    width = max(len(c.name) for c in checks)
    for c in checks:
        lines.append(f"  {MARK[c.level]} {c.name.ljust(width)}  {c.detail}")
        if c.fix and c.level != "ok":
            lines.append(f"    {'fix' if c.level == 'fail' else 'hint'}: {c.fix}")
    fails = sum(c.level == "fail" for c in checks)
    warns = sum(c.level == "warn" for c in checks)
    lines.append(f"{fails} problems, {warns} hints." if fails or warns else "ready — `sherpa plan` is the next step.")
    return "\n".join(lines) + "\n"


def render_json(checks: list[Check]) -> str:
    """The same report for scripts: ``{"sherpa", "checks": [{name, level, detail, fix}], "problems", "hints"}``."""
    out = {
        "sherpa": __version__,
        "checks": [asdict(c) for c in checks],
        "problems": sum(c.level == "fail" for c in checks),
        "hints": sum(c.level == "warn" for c in checks),
    }
    return json.dumps(out, indent=2, ensure_ascii=False) + "\n"
