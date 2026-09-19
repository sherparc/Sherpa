"""The built-in corpus of the end-to-end theses — a monorepo built programmatically, like every fixture.

It carries what the theses need and what the first e2e runs on a real repository broke on (plan §13 F49–F51):
a manifest at the root (scope ``""`` — the root ``AGENTS.md`` links its owner doc without a ``../``), an active
nested unit with two authors and a generated directory (agent, owner doc and skill proposals), a unit with
dependents, a small unit, a dormant unit, a test module more active than any business unit, a path with an
umlaut (ADR-0038) and enough commits for a detached checkout three behind the trunk. Its ``origin`` is a bare
repository next to it, so ``origin/main`` resolves and ``git fetch`` stays local. ``SHERPA_E2E_REPO`` replaces
it with a real repository — the theses are the same."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import commit, git


def build_corpus(tmp: Path) -> Path:
    work = tmp / "seed"
    work.mkdir()
    git(work, "init", "-q", "-b", "main")
    files: dict[str, str] = {"pyproject.toml": '[project]\nname = "app"\nversion = "0"\n', "app/__init__.py": ""}
    for i in range(30):
        files[f"app/mod{i:02d}.py"] = "x = 1\n"
    for name in ("pay", "core", "web", "old"):
        files[f"svc/{name}/pyproject.toml"] = f'[project]\nname = "{name}"\nversion = "0"\n' + (
            'dependencies = ["core"]\n' if name == "pay" else ""
        )
        files[f"svc/{name}/{name}/__init__.py"] = ""
    files["tests/suite/pyproject.toml"] = '[project]\nname = "suite"\nversion = "0"\ndependencies = ["pay", "core"]\n'
    files["tests/suite/test_all.py"] = "def test(): pass\n"
    for i in range(30):
        files[f"svc/pay/pay/mod{i:02d}.py"] = "x = 1\n"
    for i in range(6):
        files[f"svc/pay/pay/migrations/{i:04d}_auto.py"] = "# generated\n"
    files["svc/pay/pay/models.py"] = "class M: pass\n"
    files["svc/pay/manage.py"] = "pass\n"
    files["docs/übersicht.md"] = "# Übersicht\n"
    commit(work, "init", files, date="2025-06-01T00:00:00Z", author="A")
    for i in range(8):
        commit(work, f"app {i}", {f"app/mod{i:02d}.py": f"x = {i}  # app\n"}, date=f"2026-02-{i + 1:02d}T09:00:00Z")
    for i in range(24):
        commit(
            work,
            f"pay {i}",
            {f"svc/pay/pay/mod{i % 30:02d}.py": f"x = {i}  # pay\n"},
            date=f"2026-02-{(i % 27) + 1:02d}T10:00:00Z",
            author="AB"[i % 2],
        )
    for i in range(26):
        commit(
            work,
            f"tests {i}",
            {"tests/suite/test_all.py": f"def test(): return {i}\n"},
            date=f"2026-02-{(i % 27) + 1:02d}T11:00:00Z",
            author="C",
        )
    commit(work, "core", {"svc/core/core/x.py": "y = 1\n"}, date="2026-02-28T00:00:00Z", author="A")
    commit(work, "web", {"svc/web/web/x.py": "y = 1\n"}, date="2026-03-01T00:00:00Z", author="B")
    commit(work, "docs", {"docs/übersicht.md": "# Übersicht\n\nMore.\n"}, date="2026-03-01T12:00:00Z", author="A")
    origin = tmp / "origin.git"
    git(tmp, "clone", "-q", "--bare", str(work), str(origin))
    clone = tmp / "mono"
    git(tmp, "clone", "-q", str(origin), str(clone))
    return clone
