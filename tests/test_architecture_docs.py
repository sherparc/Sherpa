"""The architecture diagrams (ADR-0041) are Mermaid text under ``docs/architecture/``: no renderer in the toolchain,
so this keeps them honest the stdlib way — every fence names a diagram type, every ADR and relative link it
mentions exists, and the index lists every page. Rendering is checked by hand in a browser before a change."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[1] / "docs"
ARCH = DOCS / "architecture"
TYPES = ("flowchart", "graph", "sequenceDiagram", "stateDiagram-v2", "classDiagram", "erDiagram", "gantt")
PAGES = sorted(p for p in ARCH.glob("*.md") if p.name != "README.md")


def _fences(text: str) -> list[str]:
    return re.findall(r"```mermaid\n(.*?)```", text, re.S)


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_every_fence_is_a_known_diagram_without_sequence_semicolons(page: Path):
    text = page.read_text(encoding="utf-8")
    fences = _fences(text)
    assert fences, "a diagram page without a mermaid fence"
    for code in fences:
        first = code.strip().splitlines()[0].split()[0]
        assert first in TYPES, f"{page.name}: unknown diagram type {first!r}"
        if first == "sequenceDiagram":
            for line in code.splitlines():
                if "->>" in line or "-->>" in line:
                    assert ";" not in line, f"{page.name}: ';' ends a sequence statement — {line.strip()!r}"


@pytest.mark.parametrize("page", [ARCH / "README.md", *PAGES], ids=lambda p: p.name)
def test_references_resolve(page: Path):
    text = page.read_text(encoding="utf-8")
    for adr in set(re.findall(r"ADR-(\d{4})", text)):
        assert list((DOCS / "adr").glob(f"{adr}-*.md")), f"{page.name}: ADR-{adr} does not exist"
    for link in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", text):
        if link.startswith(("http://", "https://")):
            continue
        assert (page.parent / link).resolve().exists(), f"{page.name}: broken link {link}"


def test_index_lists_every_page():
    index = (ARCH / "README.md").read_text(encoding="utf-8")
    for p in PAGES:
        assert f"({p.name})" in index, f"{p.name} missing from docs/architecture/README.md"
    assert "architecture/README.md" in (DOCS / "index.md").read_text(encoding="utf-8")
