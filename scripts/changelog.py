#!/usr/bin/env python3
"""changelog — ``CHANGELOG.md`` from the trunk's history (stdlib only, deterministic; ADR-0058).

Every merge into ``main`` is a squash commit whose message is one to three full sentences naming what changed
and why (CLAUDE.md); the tags ``v<version>`` mark the releases. That is the changelog — this script only lays
it out: one section per tag, newest first, with the tag's date, one bullet per merge below it, the pull request
number as a link; commits after the last tag under ``Unreleased``. Nothing is written by hand into the file —
the sentence belongs in the commit message, once (the owner principle).

Usage:
  python3 scripts/changelog.py                 # rewrite CHANGELOG.md from `git log` of this repository
  python3 scripts/changelog.py --check         # exit 1 when CHANGELOG.md differs from what git says
  python3 scripts/changelog.py --repo <path> --out -    # render another repository to stdout

The release step of the milestone ritual runs it in the version-bump pull request: when ``__version__`` in
``src/sherpa/__init__.py`` is newer than the newest tag, the commits since that tag are the coming release and
get its heading (``## v0.8.5 — <date of HEAD>``) instead of ``Unreleased`` — the tag lands on that commit, and a
tag is lightweight, so its date is the commit's and the file stays what git says. ``release.yml`` refuses a
tag whose section is missing.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

TITLE = "# Changelog\n"
INTRO = (
    "Every entry is a merge into `main` — the squash commit's own message, written by the author of the change —\n"
    "laid out per release by [`scripts/changelog.py`](scripts/changelog.py); nothing here is edited by hand.\n"
    "Releases are the tags `v<version>`; the wheel of each is on [PyPI](https://pypi.org/project/sherparc/) and\n"
    "attached to the [GitHub release](https://github.com/sherparc/Sherpa/releases).\n"
)
PR_REF = re.compile(r"\s*\(#(\d+)\)\s*$")
VERSION = re.compile(r'__version__ = "([^"]+)"')


def git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise SystemExit(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def tags(repo: Path) -> list[tuple[str, str]]:
    """``(tag, date)`` for every ``v*`` tag, newest version first (the tag's own date, not the commit's)."""
    out = git(repo, "tag", "-l", "v*", "--sort=-version:refname", "--format=%(refname:short) %(creatordate:short)")
    return [tuple(line.split()) for line in out.splitlines() if line.strip()]  # type: ignore[misc]


def messages(repo: Path, rev_range: str) -> list[str]:
    """The subject line of every non-merge commit in the range, newest first — on a squash-merged trunk that is
    the merge message."""
    out = git(repo, "log", "--no-merges", "--format=%s", rev_range)
    return [line.strip() for line in out.splitlines() if line.strip()]


def pending_version(repo: Path, newest_tag: str | None) -> str | None:
    """``v<version>`` when the package declares a version newer than the newest tag — the release the bump
    pull request prepares — else None."""
    init = repo / "src" / "sherpa" / "__init__.py"
    if not init.is_file():
        return None
    m = VERSION.search(init.read_text(encoding="utf-8"))
    if not m:
        return None
    version = f"v{m.group(1)}"
    if newest_tag is None or _key(version) > _key(newest_tag):
        return version
    return None


def _key(tag: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", tag))


def bullet(subject: str, pulls: str) -> str:
    m = PR_REF.search(subject)
    if m:
        subject = subject[: m.start()].rstrip()
        return f"- {subject} ([#{m.group(1)}]({pulls}/{m.group(1)}))\n"
    return f"- {subject}\n"


def render(repo: Path, *, pulls: str = "https://github.com/sherparc/Sherpa/pull") -> str:
    """The whole file from the repository's tags and trunk history."""
    lines = [TITLE, "\n", INTRO]
    released = tags(repo)
    newest = released[0][0] if released else None
    unreleased = messages(repo, f"{newest}..HEAD" if newest else "HEAD")
    if unreleased:
        coming = pending_version(repo, newest)
        if coming:  # the bump pull request: the section the tag will point at
            lines.append(
                f"\n## {coming} — {git(repo, 'log', '-1', '--format=%cd', '--date=short', 'HEAD').strip()}\n\n"
            )
        else:
            lines.append("\n## Unreleased\n\n")
        lines.extend(bullet(s, pulls) for s in unreleased)
    for i, (tag, date) in enumerate(released):
        older = released[i + 1][0] if i + 1 < len(released) else None
        lines.append(f"\n## {tag} — {date}\n\n")
        entries = messages(repo, f"{older}..{tag}" if older else tag)
        lines.extend(bullet(s, pulls) for s in entries)
        if not entries:
            lines.append("- (no merge between the tags)\n")
    return "".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]), help="repository root")
    ap.add_argument("--out", help="output file; '-' = stdout (default: <repo>/CHANGELOG.md)")
    ap.add_argument("--check", action="store_true", help="exit 1 when the file differs from the rendering")
    args = ap.parse_args(argv)
    repo = Path(args.repo).resolve()
    text = render(repo)
    out = repo / "CHANGELOG.md" if not args.out else (None if args.out == "-" else Path(args.out))
    if out is None:
        sys.stdout.write(text)
        return 0
    if args.check:
        current = out.read_text(encoding="utf-8") if out.is_file() else ""
        if current != text:
            print(f"{out} is not what git says — run `python3 scripts/changelog.py`", file=sys.stderr)
            return 1
        print(f"{out} is current")
        return 0
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"→ {out} ({len(tags(repo))} releases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
