"""Distribution: where releases live, how sherpa was installed, ``self-update`` and the daily update hint.

The index is PyPI (ADR-0053): ``release.yml`` publishes the wheel of every tag, the JSON API needs no token, and the
installer fetches the wheel itself. GitHub Releases stay the fallback (ADR-0018) for a version the index does not
have yet or a machine that cannot reach it: the Releases API with a token — ``GITHUB_TOKEN``/``GH_TOKEN`` or
``gh auth token`` — else the newest tag by ``git ls-remote`` over the user's git credentials, and the install
source is the tag's git URL (ADR-0035).

The hint never blocks: the check runs in a daemon thread at most once a day, writes its result to a cache file,
and the command prints only what an earlier check has already cached. ``SHERPA_NO_UPDATE_CHECK=1`` switches it off.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sherpa import __version__, atomic

REPO = "sherparc/Sherpa"
PYPI_PROJECT = "sherparc"  # the PyPI name (ADR-0054); the CLI and the import package stay `sherpa` (ADR-0009)
PYPI_JSON = f"https://pypi.org/pypi/{PYPI_PROJECT}/json"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
GIT_URL = f"https://github.com/{REPO}.git"
GIT_URLS = (GIT_URL, f"git@github.com:{REPO}.git")  # ls-remote tries https (credential helper), then ssh
WHEEL_NAME = re.compile(r"^[A-Za-z0-9_.]+-[A-Za-z0-9_.!+]+(-\d[A-Za-z0-9_.]*)?-[^-]+-[^-]+-[^-]+\.whl$")  # PEP 427
CACHE_FILE = "update-check.json"
CHECK_INTERVAL = timedelta(hours=24)
TIMEOUT = 3.0  # seconds; the hint thread and doctor both use it
NO_CHECK_ENV = "SHERPA_NO_UPDATE_CHECK"
CACHE_DIR_ENV = "SHERPA_CACHE_DIR"


@dataclass(frozen=True)
class Release:
    version: str  # "0.5.0"
    tag: str  # "v0.5.0"
    wheel_url: str | None  # API asset URL (needs Accept: application/octet-stream), None when no wheel attached
    html_url: str
    wheel_name: str | None = None  # the asset's file name — pip reads the tags from it (PEP 427), so it must stay
    index: str = "github"  # "pypi" when the index answered — the installer then fetches the wheel itself


def parse_version(v: str) -> tuple[int, ...]:
    """Numeric parts padded to three (``v0.5`` → (0, 5, 0, 0)); a pre-release suffix sorts below the plain version
    (``0.5.0rc1`` → (0, 5, 0, -1)). Enough for our tags; not a full PEP 440 parser."""
    core = re.match(r"v?(\d+(?:\.\d+)*)", v.strip())
    if not core:
        return (0, 0, 0, 0)
    parts = tuple(int(x) for x in core.group(1).split("."))
    parts = parts + (0,) * (3 - len(parts))
    return parts + ((-1,) if len(v.strip()) > core.end() else (0,))


def is_newer(candidate: str, current: str = __version__) -> bool:
    return parse_version(candidate) > parse_version(current)


# --- token and API -------------------------------------------------------------------------------------------


def token() -> str | None:
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    gh = shutil.which("gh")
    if not gh:
        return None
    try:
        r = subprocess.run([gh, "auth", "token"], capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() or None if r.returncode == 0 else None


def _request(url: str, tok: str | None, accept: str = "application/vnd.github+json") -> urllib.request.Request:
    headers = {"Accept": accept, "User-Agent": f"sherpa/{__version__}"}
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    return urllib.request.Request(url, headers=headers)


def latest_on_index(timeout: float = TIMEOUT) -> Release | None:
    """The newest version on PyPI, or None when the index has no project yet or cannot be reached (ADR-0053) —
    the GitHub release is the fallback, never the other way round. Never raises."""
    try:
        with urllib.request.urlopen(_request(PYPI_JSON, None, "application/json"), timeout=timeout) as r:
            data = json.load(r)
    except (urllib.error.URLError, OSError, ValueError):
        return None
    version = str((data.get("info") or {}).get("version", "")) if isinstance(data, dict) else ""
    if not version:
        return None
    wheel = next((u for u in data.get("urls", []) if str(u.get("filename", "")).endswith(".whl")), None)
    return Release(
        version=version,
        tag=f"v{version}",
        wheel_url=str(wheel["url"]) if wheel else None,
        html_url=f"https://pypi.org/project/{PYPI_PROJECT}/{version}/",
        wheel_name=str(wheel["filename"]) if wheel else None,
        index="pypi",
    )


def latest_release(tok: str | None, timeout: float = TIMEOUT) -> Release:
    """The newest release: PyPI first, without a token (ADR-0053); else the GitHub API with a token, else the newest
    tag by ``git ls-remote`` through the user's git credentials (ADR-0035). Raises ``UpdateError`` with the reason
    of the last attempt (no network, no access, no release)."""
    rel = latest_on_index(timeout=timeout)
    if rel is not None:
        return rel
    if not tok:
        return latest_tag(timeout=timeout)
    try:
        with urllib.request.urlopen(_request(API_LATEST, tok), timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:  # with a token GitHub answers 404 only for "no release yet"
            raise UpdateError(f"no release published yet (https://github.com/{REPO}/releases)") from e
        hint = " — the token has no access to the repository" if e.code in (401, 403) else ""
        raise UpdateError(f"GitHub API {e.code} for {API_LATEST}{hint}") from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise UpdateError(f"GitHub unreachable ({getattr(e, 'reason', e)})") from e
    tag = str(data.get("tag_name", ""))
    if not tag:
        raise UpdateError("no release found")
    asset = next((a for a in data.get("assets", []) if str(a.get("name", "")).endswith(".whl")), None)
    return Release(
        version=tag.removeprefix("v"),
        tag=tag,
        wheel_url=asset["url"] if asset else None,
        html_url=str(data.get("html_url", "")),
        wheel_name=str(asset["name"]) if asset else None,
    )


def _run_git(cmd: list[str], timeout: float) -> subprocess.CompletedProcess:
    """Seam for tests; never prompts for credentials (``GIT_TERMINAL_PROMPT=0``)."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)


def latest_tag(timeout: float = TIMEOUT) -> Release:
    """The newest ``v*`` tag by ``git ls-remote --tags`` — no token, no API, the user's git credentials (https
    credential helper, then ssh). Never prompts (``GIT_TERMINAL_PROMPT=0``)."""
    errors = []
    for url in GIT_URLS:
        cmd = ["git", "ls-remote", "--tags", "--refs", url]
        try:
            r = _run_git(cmd, timeout)
        except (OSError, subprocess.TimeoutExpired) as e:
            errors.append(f"{url}: {getattr(e, 'strerror', None) or e.__class__.__name__}")
            continue
        if r.returncode != 0:
            last = (r.stderr or "").strip().splitlines()[-1:] or [f"exit {r.returncode}"]
            errors.append(f"{url}: {last[0][:160]}")
            continue
        tags = [line.split("refs/tags/", 1)[1] for line in r.stdout.splitlines() if "refs/tags/v" in line]
        if not tags:
            raise UpdateError(f"no release tag on {url} (https://github.com/{REPO}/releases)")
        tag = max(tags, key=parse_version)
        return Release(tag.removeprefix("v"), tag, None, f"https://github.com/{REPO}/releases/tag/{tag}")
    raise UpdateError(
        "no access without a token: `git ls-remote` failed for "
        + "; ".join(errors)
        + " — `gh auth login`, GITHUB_TOKEN, or git credentials for the repository"
    )


class UpdateError(RuntimeError):
    """The update path is blocked; the message names the reason and the fix."""


def download(rel: Release, tok: str | None, into: Path, timeout: float = 60.0) -> Path:
    """The release's wheel under its own file name: pip reads the version and the tags from the name (PEP 427);
    the API asset URL ends in a number and would make an unusable file."""
    if not rel.wheel_url:
        raise UpdateError(f"release {rel.tag} has no wheel attached")
    name = rel.wheel_name or f"{PYPI_PROJECT}-{rel.version}-py3-none-any.whl"
    if not WHEEL_NAME.match(name):
        raise UpdateError(f"{name!r} is not a valid wheel file name (PEP 427)")
    target = into / name
    try:
        with urllib.request.urlopen(_request(rel.wheel_url, tok, "application/octet-stream"), timeout=timeout) as r:
            target.write_bytes(r.read())
    except (urllib.error.URLError, OSError) as e:
        raise UpdateError(f"download failed ({getattr(e, 'reason', e)})") from e
    return target


# --- installer -----------------------------------------------------------------------------------------------


def installer() -> str:
    """How this sherpa was installed: ``uv`` (uv tool), ``pipx``, ``editable`` (a clone) or ``pip`` (any venv)."""
    prefix = sys.prefix.replace("\\", "/").lower()
    if "/uv/tools/" in prefix or prefix.endswith("/uv/tools"):
        return "uv"
    if "/pipx/venvs/" in prefix:
        return "pipx"
    src = Path(__file__).resolve()
    if src.parent.parent.name == "src" and (src.parents[2] / "pyproject.toml").is_file():
        return "editable"
    return "pip"


def install_command(kind: str, source: str) -> list[str]:
    """The command that replaces the running sherpa with ``source`` (a wheel path or a git URL)."""
    if kind == "uv":
        return ["uv", "tool", "install", "--force", "--reinstall", source]
    if kind == "pipx":
        return ["pipx", "install", "--force", source]
    return [sys.executable, "-m", "pip", "install", "--upgrade", source]


def self_update(*, check_only: bool = False, run=subprocess.run, out=None) -> int:
    """Fetch the latest release; install it with the installer that owns this copy. Exit 0 also when current."""
    out = out or sys.stdout
    kind = installer()
    if kind == "editable" and not check_only:
        clone = Path(__file__).resolve().parents[2]
        raise UpdateError(f"this sherpa runs from a clone ({clone}) — `git pull` updates it")
    tok = token()
    rel = latest_release(tok)
    if not is_newer(rel.version):
        print(f"sherpa {__version__} is current (latest release: {rel.tag}).", file=out)
        return 0
    print(f"sherpa {rel.version} is available (you have {__version__}): {rel.html_url}", file=out)
    if check_only:
        return 0
    with tempfile.TemporaryDirectory(prefix="sherpa-update-") as tmp:
        if rel.index == "pypi":
            source = f"{PYPI_PROJECT}=={rel.version}"  # the installer fetches the wheel from the index itself
        elif rel.wheel_url and tok:
            source = str(download(rel, tok, Path(tmp)))
        else:
            source = f"git+{GIT_URL}@{rel.tag}"  # no token or no wheel: the tag through the user's git credentials
        cmd = install_command(kind, source)
        print(f"→ {' '.join(cmd)}", file=out)
        r = run(cmd, text=True, capture_output=True)
    if r.returncode != 0:
        raise UpdateError(f"{cmd[0]} failed: {(r.stderr or r.stdout).strip()}")
    print(f"sherpa {rel.version} installed via {kind}.", file=out)
    return 0


# --- daily hint ----------------------------------------------------------------------------------------------


def cache_dir() -> Path:
    if os.environ.get(CACHE_DIR_ENV):
        return Path(os.environ[CACHE_DIR_ENV])
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "sherpa"


def read_cache() -> dict:
    try:
        return json.loads((cache_dir() / CACHE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _check_and_cache() -> None:
    """The thread body: one API call, the result (or the failure) into the cache. Never raises."""
    entry = {"checked": datetime.now(UTC).isoformat(timespec="seconds"), "latest": None}
    try:
        entry["latest"] = latest_release(token()).version
    except UpdateError as e:
        entry["error"] = str(e)
    try:
        atomic.write_text(cache_dir() / CACHE_FILE, json.dumps(entry, indent=2) + "\n")
    except OSError:
        pass


def hint_enabled(cmd: str, stream=None) -> bool:
    """Only interactive runs of the everyday commands: never in CI, hooks, pipes, or `doctor`/`self-update`."""
    stream = stream or sys.stderr
    if os.environ.get(NO_CHECK_ENV) or os.environ.get("CI"):
        return False
    if cmd in ("doctor", "self-update", "check"):
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


def start_check(cmd: str) -> threading.Thread | None:
    """Kick off the daily check in the background when it is due; returns the thread (tests join it)."""
    if not hint_enabled(cmd):
        return None
    checked = read_cache().get("checked")
    if checked:
        try:
            if datetime.now(UTC) - datetime.fromisoformat(checked) < CHECK_INTERVAL:
                return None
        except ValueError:
            pass
    t = threading.Thread(target=_check_and_cache, name="sherpa-update-check", daemon=True)
    t.start()
    return t


def hint(cmd: str, stream=None) -> str | None:
    """The one-line hint from the cache, or None. Printed after the command's own output."""
    if not hint_enabled(cmd, stream):
        return None
    latest = read_cache().get("latest")
    if latest and is_newer(latest):
        return (
            f"sherpa {latest} is available (you have {__version__}) — `sherpa self-update`; "
            f"{NO_CHECK_ENV}=1 hides this."
        )
    return None
