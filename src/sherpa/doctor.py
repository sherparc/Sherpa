"""``sherpa doctor`` — every prerequisite as one line with a fix; the first command a new user runs.

Levels: ``ok`` (✓), ``warn`` (!) for things sherpa works without but the user should know, ``fail`` (✗) for what
blocks ``scan``. Exit 1 only on a fail. Checks are pure functions over the environment so tests can run them one
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
    """Which agent runtime the harness will be projected into — informational, sherpa works without one."""
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
    return Check("runtime", "ok", ", ".join(found))


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
    return Check("update", "ok", f"{__version__} is current (via {'the API' if tok else 'git ls-remote'})")


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
