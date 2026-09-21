"""``scripts/changelog.py`` — CHANGELOG.md from the trunk's tags and squash-merge messages (ADR-0058)."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

from tests.conftest import commit, git

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "changelog.py"
spec = importlib.util.spec_from_file_location("changelog", SCRIPT)
changelog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(changelog)  # type: ignore[union-attr]

PULLS = "https://example.test/pull"


def trunk(tmp_path: Path, version: str = "0.1.0") -> Path:
    """A trunk with two tagged releases and one merge after the last tag; ``__version__`` as given."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    init = {"src/sherpa/__init__.py": f'__version__ = "{version}"\n'}
    commit(repo, "M0: skeleton, ADRs, the plan. (#1)", init, date="2026-01-01T10:00:00Z")
    git(repo, "tag", "v0.1.0")
    commit(repo, "M1: the scanner. (#2)", {"a.py": "x\n"}, date="2026-01-02T10:00:00Z")
    commit(repo, "M1a: modules from manifests. (#3)", {"b.py": "x\n"}, date="2026-01-03T10:00:00Z")
    git(repo, "tag", "v0.2.0")
    commit(repo, "A fix without a pull request number.", {"c.py": "x\n"}, date="2026-01-04T10:00:00Z")
    return repo


def test_render_one_section_per_tag_newest_first_with_linked_pull_requests(tmp_path: Path):
    repo = trunk(tmp_path, "0.2.0")
    text = changelog.render(repo, pulls=PULLS)
    assert text.startswith("# Changelog\n\n") and "scripts/changelog.py" in text
    assert text.split("\n## ")[1:] == [
        "Unreleased\n\n- A fix without a pull request number.\n",
        f"v0.2.0 — 2026-01-03\n\n- M1a: modules from manifests. ([#3]({PULLS}/3))\n- M1: the scanner. ([#2]({PULLS}/2))\n",
        f"v0.1.0 — 2026-01-01\n\n- M0: skeleton, ADRs, the plan. ([#1]({PULLS}/1))\n",
    ]
    assert changelog.render(repo, pulls=PULLS) == text  # deterministic


def test_a_bumped_version_heads_the_coming_release_instead_of_unreleased(tmp_path: Path):
    """The bump pull request renders the section the tag will point at; the tag is lightweight, so its date is
    the commit's and the file stays what git says after the tag."""
    repo = trunk(tmp_path, "0.3.0")
    before = changelog.render(repo, pulls=PULLS)
    assert "\n## v0.3.0 — 2026-01-04\n\n- A fix without a pull request number.\n" in before
    assert "Unreleased" not in before
    git(repo, "tag", "v0.3.0")
    assert changelog.render(repo, pulls=PULLS) == before


def test_no_merge_between_two_tags_is_said(tmp_path: Path):
    repo = trunk(tmp_path, "0.2.0")
    git(repo, "tag", "v0.2.1")
    assert "\n## v0.2.1 — 2026-01-04\n\n- A fix without a pull request number.\n" in changelog.render(repo, pulls=PULLS)
    git(repo, "tag", "v0.2.2")  # same commit as v0.2.1
    assert "\n## v0.2.2 — 2026-01-04\n\n- (no merge between the tags)\n" in changelog.render(repo, pulls=PULLS)


def test_main_writes_checks_and_prints(tmp_path: Path, capsys):
    repo = trunk(tmp_path, "0.2.0")
    assert changelog.main(["--repo", str(repo)]) == 0
    out = repo / "CHANGELOG.md"
    assert out.is_file() and capsys.readouterr().out.strip().endswith("(2 releases)")
    assert changelog.main(["--repo", str(repo), "--check"]) == 0
    assert capsys.readouterr().out.strip().endswith("is current")
    commit(repo, "Another merge. (#4)", {"d.py": "x\n"}, date="2026-01-05T10:00:00Z")
    assert changelog.main(["--repo", str(repo), "--check"]) == 1
    assert "run `python3 scripts/changelog.py`" in capsys.readouterr().err
    assert changelog.main(["--repo", str(repo), "--out", "-"]) == 0
    assert "- Another merge. ([#4](https://github.com/sherparc/Sherpa/pull/4))" in capsys.readouterr().out


def test_the_checked_in_changelog_is_what_git_says():
    """The file in the repository is current — regenerated in every version-bump pull request; a merge without
    a bump leaves its entry under ``Unreleased`` until the next one, which is fine, but the file must never
    say something git does not."""
    root = SCRIPT.parents[1]
    if subprocess.run(["git", "-C", str(root), "tag", "-l", "v*"], capture_output=True, text=True).stdout.strip() == "":
        return  # a clone without tags (CI fetches one commit) cannot render the history
    current = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    rendered = changelog.render(root)
    released = [ln for ln in rendered.splitlines() if ln.startswith("## v")]
    assert all(ln in current for ln in released), "a release section is missing — run python3 scripts/changelog.py"
