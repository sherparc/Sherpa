"""Distribution: version order, installer detection, the Releases API client, self-update and the daily hint.

The API is mocked through ``urllib.request.urlopen``; no test reaches the network (conftest sets
``SHERPA_NO_UPDATE_CHECK``; the tests that exercise the hint delete it again and point the cache at tmp).
"""

from __future__ import annotations

import io
import json
import sys
import urllib.error
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sherpa import __version__, cli, update

NEWER = "99.0.0"


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _fake_api(
    monkeypatch, *, tag=f"v{NEWER}", wheel=True, status=None, raise_url=False, seen=None, git=None, pypi=None
):
    """PyPI (``pypi``: the version on the index, or None for "no project yet" — a 404), the Releases API and, for
    the tokenless path, ``git ls-remote`` (``git``: a list of tags, or None for the same failure the API would
    show — a URLError becomes an OSError, a status becomes exit 128)."""

    class Ran:
        def __init__(self, code, out="", err=""):
            self.returncode, self.stdout, self.stderr = code, out, err

    def run_git(cmd, timeout):
        if seen is not None:
            seen.append(cmd)
        if raise_url:
            raise OSError(2, "No such file or directory")
        if status:
            return Ran(128, err="fatal: could not read Username for 'https://github.com': terminal prompts disabled")
        tags = git if git is not None else ([tag, "v0.1.0", "v0.1.0rc1"] if tag else [])
        return Ran(0, out="".join(f"{'0' * 40}\trefs/tags/{t}\n" for t in tags))

    monkeypatch.setattr(update, "_run_git", run_git)

    def urlopen(req, timeout=0):
        if seen is not None:
            seen.append(req)
        if raise_url:
            raise urllib.error.URLError("no route to host")
        if req.full_url == update.PYPI_JSON:
            if pypi is None:
                raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)
            urls = (
                [{"filename": f"{update.PYPI_PROJECT}-{pypi}-py3-none-any.whl", "url": "https://files/x.whl"}]
                if wheel
                else []
            )
            return _Resp(json.dumps({"info": {"version": pypi}, "urls": urls}).encode())
        if status:
            raise urllib.error.HTTPError(req.full_url, status, "nope", {}, None)
        if req.full_url.endswith("/assets/1"):
            return _Resp(b"WHEELBYTES")
        assets = (
            [{"name": f"{update.PYPI_PROJECT}-{tag[1:]}-py3-none-any.whl", "url": "https://api/assets/1"}]
            if wheel
            else []
        )
        body = {"tag_name": tag, "html_url": f"https://github.com/{update.REPO}/releases/tag/{tag}", "assets": assets}
        return _Resp(json.dumps(body).encode())

    monkeypatch.setattr(update.urllib.request, "urlopen", urlopen)


@pytest.mark.parametrize(
    "a,b,newer",
    [
        ("0.5.0", "0.4.0", True),
        ("v0.5.0", "0.5.0", False),
        ("0.10.0", "0.9.9", True),
        ("0.5.0rc1", "0.5.0", False),
        ("0.5.0", "0.5.0rc1", True),
        ("garbage", "0.4.0", False),
        ("1.0", "0.99.99", True),
    ],
)
def test_version_order(a, b, newer):
    assert update.is_newer(a, b) is newer


def test_parse_version_prerelease_sorts_below_release():
    assert update.parse_version("v1.2.3") == (1, 2, 3, 0)
    assert update.parse_version("1.2.3rc1") < update.parse_version("1.2.3")


def test_token_prefers_env_then_gh(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t-env")
    assert update.token() == "t-env"
    monkeypatch.delenv("GITHUB_TOKEN")
    monkeypatch.setenv("GH_TOKEN", "t-gh-env")
    assert update.token() == "t-gh-env"
    monkeypatch.delenv("GH_TOKEN")
    monkeypatch.setattr(update.shutil, "which", lambda _: None)
    assert update.token() is None
    monkeypatch.setattr(update.shutil, "which", lambda _: "/usr/bin/gh")

    class R:
        returncode, stdout = 0, "t-cli\n"

    monkeypatch.setattr(update.subprocess, "run", lambda *a, **k: R())
    assert update.token() == "t-cli"

    def boom(*a, **k):
        raise OSError("gone")

    monkeypatch.setattr(update.subprocess, "run", boom)
    assert update.token() is None


def test_latest_release_parses_tag_and_wheel(monkeypatch):
    seen = []
    _fake_api(monkeypatch, seen=seen)
    rel = update.latest_release("tok")
    assert rel == update.Release(
        NEWER,
        f"v{NEWER}",
        "https://api/assets/1",
        f"https://github.com/{update.REPO}/releases/tag/v{NEWER}",
        f"{update.PYPI_PROJECT}-{NEWER}-py3-none-any.whl",
    )
    assert seen[0].full_url == update.PYPI_JSON and seen[0].get_header("Authorization") is None  # the index first
    assert seen[1].get_header("Authorization") == "Bearer tok"
    _fake_api(monkeypatch, wheel=False)
    assert update.latest_release("tok").wheel_url is None and update.latest_release("tok").wheel_name is None


def test_latest_release_without_token_uses_git_ls_remote(monkeypatch):
    """ADR-0035: no token → no GitHub API call; the newest ``v*`` tag by version order, pre-releases below."""
    seen = []
    _fake_api(monkeypatch, seen=seen, git=["v0.9.0", f"v{NEWER}", "v0.10.0rc1", "v0.2.0"])
    rel = update.latest_release(None)
    assert rel.tag == f"v{NEWER}" and rel.wheel_url is None and rel.wheel_name is None
    assert rel.html_url == f"https://github.com/{update.REPO}/releases/tag/v{NEWER}"
    assert seen[0].full_url == update.PYPI_JSON  # the index first, silent here (ADR-0053)
    assert seen[1:] == [["git", "ls-remote", "--tags", "--refs", update.GIT_URL]]


def test_latest_release_prefers_pypi_without_a_token(monkeypatch):
    """ADR-0053: the index answers → no GitHub API call, no git, no token needed; the wheel comes from the index."""
    seen = []
    _fake_api(monkeypatch, seen=seen, pypi=NEWER, git=[])
    rel = update.latest_release(None)
    assert rel == update.Release(
        NEWER,
        f"v{NEWER}",
        "https://files/x.whl",
        f"https://pypi.org/project/{update.PYPI_PROJECT}/{NEWER}/",
        f"{update.PYPI_PROJECT}-{NEWER}-py3-none-any.whl",
        "pypi",
    )
    assert [getattr(r, "full_url", r) for r in seen] == [update.PYPI_JSON]
    assert update.latest_release("tok") == rel  # a token changes nothing while the index answers


@pytest.mark.parametrize("body", [b"{}", b'{"info": {}}', b"[]", b"garbage"])
def test_latest_on_index_is_none_on_an_answer_without_a_version(monkeypatch, body):
    monkeypatch.setattr(update.urllib.request, "urlopen", lambda req, timeout=0: _Resp(body))
    assert update.latest_on_index() is None


def test_latest_release_falls_back_to_github_when_the_index_is_silent(monkeypatch):
    """No project on PyPI yet (404) or no route to it: the GitHub path answers exactly as before ADR-0053."""
    seen = []
    _fake_api(monkeypatch, seen=seen)  # pypi=None → 404
    assert update.latest_release("tok").index == "github"
    assert seen[0].full_url == update.PYPI_JSON and seen[1].full_url == update.API_LATEST


def test_self_update_installs_from_pypi_by_version(monkeypatch):
    """The installer fetches the wheel itself: no download, the source is the pinned requirement."""
    monkeypatch.setattr(update, "installer", lambda: "uv")
    monkeypatch.setattr(update, "token", lambda: None)
    _fake_api(monkeypatch, pypi=NEWER)
    calls = []

    class R:
        returncode, stdout, stderr = 0, "", ""

    out = io.StringIO()
    assert update.self_update(run=lambda cmd, **k: calls.append(cmd) or R(), out=out) == 0
    assert calls == [["uv", "tool", "install", "--force", "--reinstall", f"{update.PYPI_PROJECT}=={NEWER}"]]
    assert f"https://pypi.org/project/{update.PYPI_PROJECT}/{NEWER}/" in out.getvalue()


def test_latest_tag_tries_ssh_after_https_and_names_both_failures(monkeypatch):
    calls = []

    class Ran:
        returncode, stdout, stderr = 128, "", "fatal: Authentication failed"

    monkeypatch.setattr(update, "_run_git", lambda cmd, timeout: calls.append(cmd[-1]) or Ran())
    with pytest.raises(update.UpdateError, match="no access without a token") as e:
        update.latest_tag()
    assert calls == list(update.GIT_URLS)
    assert "Authentication failed" in str(e.value) and "gh auth login" in str(e.value)
    _fake_api(monkeypatch, git=[])
    with pytest.raises(update.UpdateError, match="no release tag"):
        update.latest_tag()


@pytest.mark.parametrize(
    "status,tok,needle",
    [
        (404, None, "no access without a token"),
        (404, "tok", "no release published yet"),
        (401, "tok", "token has no access"),
        (500, "tok", "GitHub API 500"),
    ],
)
def test_latest_release_http_errors_name_the_fix(monkeypatch, status, tok, needle):
    _fake_api(monkeypatch, status=status)
    with pytest.raises(update.UpdateError, match=needle):
        update.latest_release(tok)


def test_latest_release_unreachable_and_empty(monkeypatch):
    _fake_api(monkeypatch, raise_url=True)
    with pytest.raises(update.UpdateError, match="unreachable"):
        update.latest_release("tok")
    with pytest.raises(update.UpdateError, match="No such file"):
        update.latest_release(None)  # no git at all
    _fake_api(monkeypatch, tag="")
    with pytest.raises(update.UpdateError, match="no release"):
        update.latest_release("tok")
    with pytest.raises(update.UpdateError, match="no release tag"):
        update.latest_release(None)


def _release(**kw) -> update.Release:
    base = dict(
        version=NEWER,
        tag=f"v{NEWER}",
        wheel_url="https://api/assets/1",
        html_url="",
        wheel_name=f"{update.PYPI_PROJECT}-{NEWER}-py3-none-any.whl",
    )
    return update.Release(**(base | kw))


def test_download_writes_wheel_under_its_pep427_name(monkeypatch, tmp_path: Path):
    """The API asset URL ends in a number; pip needs ``dist-version-py-abi-plat.whl`` to accept the file."""
    seen = []
    _fake_api(monkeypatch, seen=seen)
    p = update.download(_release(), "tok", tmp_path)
    assert p.read_bytes() == b"WHEELBYTES" and p.name == f"{update.PYPI_PROJECT}-{NEWER}-py3-none-any.whl"
    assert seen[0].get_header("Accept") == "application/octet-stream"
    assert update.WHEEL_NAME.match(p.name)
    assert update.download(_release(wheel_name=None), "tok", tmp_path).name == p.name  # derived from the version
    with pytest.raises(update.UpdateError, match="not a valid wheel file name"):
        update.download(_release(wheel_name="sherpa_harness.whl"), "tok", tmp_path)
    with pytest.raises(update.UpdateError, match="no wheel attached"):
        update.download(_release(wheel_url=None), "tok", tmp_path)
    _fake_api(monkeypatch, raise_url=True)
    with pytest.raises(update.UpdateError, match="download failed"):
        update.download(_release(), "tok", tmp_path)


@pytest.mark.parametrize(
    "name,ok",
    [
        ("sherpa_harness-0.7.2-py3-none-any.whl", True),
        ("sherpa_harness-0.7.2-1-py3-none-any.whl", True),
        ("sherpa_harness-0.7.2rc1-py3-none-any.whl", True),
        ("sherpa_harness.whl", False),
        ("570259520", False),
        ("sherpa_harness-0.7.2.whl", False),
    ],
)
def test_wheel_name_pattern_is_pep427(name, ok):
    assert bool(update.WHEEL_NAME.match(name)) is ok


@pytest.mark.parametrize(
    "prefix,kind",
    [("/home/u/.local/share/uv/tools/sherparc", "uv"), (r"C:\Users\u\pipx\venvs\sherparc", "pipx")],
)
def test_installer_from_prefix(monkeypatch, prefix, kind):
    monkeypatch.setattr(update.sys, "prefix", prefix)
    assert update.installer() == kind


def test_installer_editable_in_this_repo():
    assert update.installer() == "editable"  # the test suite runs from the clone


def test_installer_pip_when_not_a_clone(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(update.sys, "prefix", str(tmp_path / "venv"))
    monkeypatch.setattr(update, "__file__", str(tmp_path / "venv" / "lib" / "site-packages" / "sherpa" / "update.py"))
    assert update.installer() == "pip"


def test_install_command_per_installer():
    assert update.install_command("uv", "x.whl") == ["uv", "tool", "install", "--force", "--reinstall", "x.whl"]
    assert update.install_command("pipx", "x.whl") == ["pipx", "install", "--force", "x.whl"]
    assert update.install_command("pip", "x.whl") == [sys.executable, "-m", "pip", "install", "--upgrade", "x.whl"]


def test_self_update_refuses_editable(monkeypatch):
    _fake_api(monkeypatch)
    with pytest.raises(update.UpdateError, match="git pull"):
        update.self_update()


def test_self_update_check_only_and_current(monkeypatch):
    monkeypatch.setattr(update, "installer", lambda: "uv")
    monkeypatch.setattr(update, "token", lambda: "tok")
    _fake_api(monkeypatch)
    out = io.StringIO()
    assert update.self_update(check_only=True, out=out) == 0
    assert f"{NEWER} is available (you have {__version__})" in out.getvalue()
    _fake_api(monkeypatch, tag=f"v{__version__}")
    out = io.StringIO()
    assert update.self_update(out=out) == 0
    assert "is current" in out.getvalue()


def test_self_update_installs_wheel_with_token(monkeypatch):
    monkeypatch.setattr(update, "installer", lambda: "uv")
    monkeypatch.setattr(update, "token", lambda: "tok")
    _fake_api(monkeypatch)
    calls = []

    class R:
        returncode, stdout, stderr = 0, "", ""

    def run(cmd, **k):
        calls.append(cmd)
        assert Path(cmd[-1]).read_bytes() == b"WHEELBYTES"  # the wheel exists while the installer runs
        return R()

    out = io.StringIO()
    assert update.self_update(run=run, out=out) == 0
    assert calls[0][:5] == ["uv", "tool", "install", "--force", "--reinstall"]
    assert Path(calls[0][-1]).name == f"{update.PYPI_PROJECT}-{NEWER}-py3-none-any.whl"
    assert f"sherpa {NEWER} installed via uv." in out.getvalue()


def test_self_update_falls_back_to_git_tag_without_token(monkeypatch):
    monkeypatch.setattr(update, "installer", lambda: "pipx")
    monkeypatch.setattr(update, "token", lambda: None)
    _fake_api(monkeypatch)
    calls = []

    class R:
        returncode, stdout, stderr = 0, "", ""

    assert update.self_update(run=lambda cmd, **k: calls.append(cmd) or R(), out=io.StringIO()) == 0
    assert calls == [["pipx", "install", "--force", f"git+{update.GIT_URL}@v{NEWER}"]]


def test_self_update_reports_installer_failure(monkeypatch):
    monkeypatch.setattr(update, "installer", lambda: "pip")
    monkeypatch.setattr(update, "token", lambda: None)
    _fake_api(monkeypatch, wheel=False)

    class R:
        returncode, stdout, stderr = 1, "", "no space left"

    with pytest.raises(update.UpdateError, match="no space left"):
        update.self_update(run=lambda cmd, **k: R(), out=io.StringIO())


# --- cache and hint --------------------------------------------------------------------------------------------


def test_cache_dir_env_xdg_and_windows(monkeypatch, tmp_path: Path):
    monkeypatch.setenv(update.CACHE_DIR_ENV, str(tmp_path / "c"))
    assert update.cache_dir() == tmp_path / "c"
    monkeypatch.delenv(update.CACHE_DIR_ENV)
    monkeypatch.setattr(update.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    assert update.cache_dir() == tmp_path / "xdg" / "sherpa"
    monkeypatch.delenv("XDG_CACHE_HOME")
    assert update.cache_dir() == Path.home() / ".cache" / "sherpa"
    monkeypatch.setattr(update.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "la"))
    assert update.cache_dir() == tmp_path / "la" / "sherpa"


class _Tty(io.StringIO):
    def isatty(self):
        return True


def _enable_hint(monkeypatch):
    monkeypatch.delenv(update.NO_CHECK_ENV)
    monkeypatch.delenv("CI", raising=False)


def test_hint_enabled_rules(monkeypatch):
    _enable_hint(monkeypatch)
    assert update.hint_enabled("plan", _Tty())
    assert not update.hint_enabled("plan", io.StringIO())  # a pipe: hooks, CI logs
    for cmd in ("doctor", "self-update", "check"):
        assert not update.hint_enabled(cmd, _Tty())
    monkeypatch.setenv("CI", "true")
    assert not update.hint_enabled("plan", _Tty())
    monkeypatch.delenv("CI")
    monkeypatch.setenv(update.NO_CHECK_ENV, "1")
    assert not update.hint_enabled("plan", _Tty())


def test_start_check_writes_cache_once_a_day(monkeypatch):
    _enable_hint(monkeypatch)
    monkeypatch.setattr(update.sys, "stderr", _Tty())
    monkeypatch.setattr(update, "token", lambda: None)
    _fake_api(monkeypatch)
    t = update.start_check("plan")
    assert t is not None
    t.join(5)
    cache = update.read_cache()
    assert cache["latest"] == NEWER and "error" not in cache
    assert update.start_check("plan") is None  # checked less than 24 h ago
    assert update.hint("plan", _Tty()) == (
        f"sherpa {NEWER} is available (you have {__version__}) — `sherpa self-update`; {update.NO_CHECK_ENV}=1 hides this."
    )


def test_start_check_records_failure_and_hint_stays_quiet(monkeypatch):
    _enable_hint(monkeypatch)
    monkeypatch.setattr(update.sys, "stderr", _Tty())
    monkeypatch.setattr(update, "token", lambda: None)
    _fake_api(monkeypatch, status=404)
    t = update.start_check("plan")
    t.join(5)
    cache = update.read_cache()
    assert cache["latest"] is None and "no access without a token" in cache["error"]
    assert update.hint("plan", _Tty()) is None


def test_stale_or_broken_cache_triggers_a_new_check(monkeypatch):
    _enable_hint(monkeypatch)
    monkeypatch.setattr(update.sys, "stderr", _Tty())
    monkeypatch.setattr(update, "token", lambda: None)
    _fake_api(monkeypatch, tag=f"v{__version__}")
    old = (datetime.now(UTC) - timedelta(days=2)).isoformat(timespec="seconds")
    update.atomic.write_text(update.cache_dir() / update.CACHE_FILE, json.dumps({"checked": old, "latest": NEWER}))
    assert update.hint("plan", _Tty())  # the stale cache still hints until the new result lands
    t = update.start_check("plan")
    t.join(5)
    assert update.read_cache()["latest"] == __version__ and update.hint("plan", _Tty()) is None
    update.atomic.write_text(update.cache_dir() / update.CACHE_FILE, "{not json")
    assert update.read_cache() == {}
    update.atomic.write_text(update.cache_dir() / update.CACHE_FILE, json.dumps({"checked": "yesterday-ish"}))
    assert update.start_check("plan") is not None


def test_hint_disabled_when_env_set(monkeypatch):
    assert update.start_check("plan") is None
    assert update.hint("plan", _Tty()) is None


# --- CLI ------------------------------------------------------------------------------------------------------


def test_cli_self_update_check(monkeypatch, capsys):
    monkeypatch.setattr(update, "installer", lambda: "uv")
    monkeypatch.setattr(update, "token", lambda: "tok")
    _fake_api(monkeypatch)
    assert cli.main(["self-update", "--check"]) == 0
    assert NEWER in capsys.readouterr().out


def test_cli_self_update_error_is_exit_1(monkeypatch, capsys):
    _fake_api(monkeypatch, raise_url=True)
    monkeypatch.setattr(update, "token", lambda: None)
    monkeypatch.setattr(update, "installer", lambda: "uv")
    assert cli.main(["self-update"]) == 1
    assert "sherpa self-update: no access without a token" in capsys.readouterr().err


def test_cli_prints_hint_after_command(monkeypatch, capsys, make_origin, make_clone):
    _enable_hint(monkeypatch)
    origin, _ = make_origin()
    repo = make_clone(origin)
    update.atomic.write_text(
        update.cache_dir() / update.CACHE_FILE,
        json.dumps({"checked": datetime.now(UTC).isoformat(timespec="seconds"), "latest": NEWER}),
    )
    monkeypatch.setattr(cli.sys, "stderr", _Tty())
    assert cli.main(["scan", str(repo), "--no-fetch", "--out", "-"]) == 0
    assert f"sherpa {NEWER} is available" in cli.sys.stderr.getvalue()
