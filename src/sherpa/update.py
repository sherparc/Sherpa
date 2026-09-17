"""Distribution: where releases live, how sherpa was installed, ``self-update`` and the daily update hint.

Releases are GitHub Releases of ``sherparc/Sherpa`` (ADR-0018): ``release.yml`` attaches the wheel to the tag.
The repository is private until the public release (ADR-0010), so the Releases API needs a token —
``GITHUB_TOKEN``/``GH_TOKEN`` or ``gh auth token``. Without a token ``self-update`` falls back to the git URL of
the tag, which uses the user's git credentials.

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
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
GIT_URL = f"https://github.com/{REPO}.git"
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


def latest_release(tok: str | None, timeout: float = TIMEOUT) -> Release:
    """The newest GitHub release; raises ``UpdateError`` with the reason (no network, no token, no release)."""
    try:
        with urllib.request.urlopen(_request(API_LATEST, tok), timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404 and tok:  # GitHub answers 404 for "no release yet" as well as for "no access"
            raise UpdateError(f"no release published yet (https://github.com/{REPO}/releases)") from e
        hint = ""
        if e.code in (401, 403, 404):
            hint = " — a token is needed for the private repository (GITHUB_TOKEN or `gh auth login`)"
        raise UpdateError(f"GitHub API {e.code} for {API_LATEST}{hint}") from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise UpdateError(f"GitHub unreachable ({getattr(e, 'reason', e)})") from e
    tag = str(data.get("tag_name", ""))
    if not tag:
        raise UpdateError("no release found")
    wheel = next((a["url"] for a in data.get("assets", []) if str(a.get("name", "")).endswith(".whl")), None)
    return Release(version=tag.removeprefix("v"), tag=tag, wheel_url=wheel, html_url=str(data.get("html_url", "")))


class UpdateError(RuntimeError):
    """The update path is blocked; the message names the reason and the fix."""


def download(url: str, tok: str | None, into: Path, timeout: float = 60.0) -> Path:
    name = url.rsplit("/", 1)[-1]
    target = into / (name if name.endswith(".whl") else "sherpa_harness.whl")
    try:
        with urllib.request.urlopen(_request(url, tok, "application/octet-stream"), timeout=timeout) as r:
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
        if rel.wheel_url and tok:
            source = str(download(rel.wheel_url, tok, Path(tmp)))
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
