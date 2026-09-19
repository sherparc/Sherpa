"""The README's demo card (``scripts/render-demo.py``): the real output rendered as an SVG, deterministic, no home path."""

from __future__ import annotations

import importlib.util
import xml.dom.minidom
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "render-demo.py"
spec = importlib.util.spec_from_file_location("render_demo", SCRIPT)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)

OUTPUT = (
    "harness-plan.yaml — 2 proposals, 1 reasoned no's\n"
    "  + owner-doc  pay   24 commits/90d, 1 dependents ✓ · 40 files ✓\n"
    "  - owner-doc  web   1 commits/90d, 0 dependents ✓ · 3 files ✗\n"
    "  1 small units without owner doc (< 5 files, 0 dependents): web — listed above as no's; "
    "owner_doc_min_files in sherpa.toml [plan] moves the floor, a dependent overrides it.\n"
    "→ /repo/.sherpa/harness-plan.yaml (1 decisions kept)\n"
)


def test_wrap_keeps_every_word_and_hangs_the_continuation():
    long = "  " + " ".join(f"word{i}" for i in range(40))
    pieces = demo.wrap(long, cols=60)
    assert all(len(p) <= 60 for p in pieces) and len(pieces) > 1
    assert pieces[1].startswith("    word") and " ".join(" ".join(pieces).split()) == " ".join(long.split())
    assert demo.wrap("short") == ["short"]
    assert demo.wrap("x" * 70, cols=60) == ["x" * 60, "  " + "x" * 10]  # no space to cut at: cut hard


def test_colours_follow_the_console():
    c = demo.COLOURS
    assert demo.colour_of("  + owner-doc  pay   …") == c["add"]
    assert demo.colour_of("  - owner-doc  web   …") == c["no"]
    assert demo.colour_of("  1 small units without owner doc") == c["dim"]
    assert demo.colour_of("→ .sherpa/harness-plan.yaml") == c["arrow"]
    assert demo.colour_of("harness-plan.yaml — 2 proposals") == c["fg"]
    assert demo.spans("a ✓ b ✗", "#fff").count("<tspan") == 4 and f'fill="{c["bad"]}">✗' in demo.spans("✗", "#fff")


def test_normalise_drops_the_repository_path():
    assert demo.normalise("→ /repo/.sherpa/x (1)\n/repo\n", Path("/repo")) == "→ .sherpa/x (1)\n.\n"


def test_render_is_deterministic_valid_xml_and_carries_every_line():
    svg = demo.render("sherpa plan .", demo.normalise(OUTPUT, Path("/repo")), title="t — 2026-01-01")
    assert svg == demo.render("sherpa plan .", demo.normalise(OUTPUT, Path("/repo")), title="t — 2026-01-01")
    xml.dom.minidom.parseString(svg)  # well-formed
    assert "/repo" not in svg and "$ sherpa plan ." in svg and "harness-plan.yaml (1 decisions kept)" in svg
    assert svg.count("<text ") == 1 + 1 + 1 + 1 + 1 + 2 + 1  # title, prompt, header, +, -, the note wrapped in two, →
    assert "&lt;" in svg  # `< 5 files` is escaped


def test_the_checked_in_card_matches_the_script_and_names_no_home(tmp_path: Path):
    card = (SCRIPT.parent.parent / "assets" / "demo.svg").read_text(encoding="utf-8")
    assert "/home/" not in card and "Users" not in card and card.startswith("<svg ")
    xml.dom.minidom.parseString(card)
