#!/usr/bin/env python3
"""render-demo — the README's demo card: the real output of ``sherpa plan`` on this repository as an SVG (stdlib only).

The card is a picture of a terminal, nothing more: the command as the prompt line, every line of the output as
it was printed, coloured the way the console colours it (``+`` proposals, ``-`` reasoned no's, ``✓``/``✗``
evidence, the notes dimmed). Long lines wrap at ``COLS`` with a hanging indent — nothing is cut, nothing is
added, and the same output renders the same bytes, so the file is diffed like a golden. The only normalisation
is the repository's absolute path, which becomes ``.``: the card must not carry a home directory.

Usage:
  python3 scripts/render-demo.py                       # runs `sherpa plan .` here → assets/demo.svg
  python3 scripts/render-demo.py --out P               # another target
  sherpa plan . | python3 scripts/render-demo.py -     # render given output (the `→` line is normalised too)
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLS = 112
CHAR_W = 7.85  # px per column at 13px in the monospace stack below; Menlo/Consolas/DejaVu agree within a pixel
LINE_H = 19
PAD = 18
HEADER_H = 40
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"
COLOURS = {
    "fg": "#c9d1d9",
    "dim": "#8b949e",
    "add": "#3fb950",
    "no": "#f85149",
    "ok": "#3fb950",
    "bad": "#f85149",
    "prompt": "#79c0ff",
    "arrow": "#d2a8ff",
    "bg": "#0d1117",
    "frame": "#30363d",
}
MARK = re.compile(r"(✓|✗)")


def wrap(line: str, cols: int = COLS) -> list[str]:
    """Wrap at the last space before ``cols``; continuation lines keep the line's indent plus two."""
    indent = len(line) - len(line.lstrip(" "))
    hang = " " * (indent + 2)
    out, rest = [], line
    while len(rest) > cols:
        cut = rest.rfind(" ", 0, cols)
        if cut <= indent:
            cut = cols
        out.append(rest[:cut].rstrip())
        rest = hang + rest[cut:].lstrip()
    out.append(rest)
    return out


def colour_of(line: str) -> str:
    s = line.lstrip()
    if s.startswith("+ "):
        return COLOURS["add"]
    if s.startswith("- "):
        return COLOURS["no"]
    if s.startswith("→"):
        return COLOURS["arrow"]
    if line.startswith("  ") and s[:1] not in "+-":
        return COLOURS["dim"]
    return COLOURS["fg"]


def spans(text: str, base: str) -> str:
    """The line as tspans: the evidence marks in their own colour, everything else in the line's."""
    parts = []
    for piece in MARK.split(text):
        if not piece:
            continue
        colour = COLOURS["ok"] if piece == "✓" else COLOURS["bad"] if piece == "✗" else base
        parts.append(f'<tspan fill="{colour}">{html.escape(piece, quote=False)}</tspan>')
    return "".join(parts)


def render(command: str, output: str, *, title: str) -> str:
    rows: list[tuple[str, str]] = [(f"$ {command}", COLOURS["prompt"])]
    for line in output.rstrip("\n").split("\n"):
        base = colour_of(line)
        rows.extend((piece, base) for piece in wrap(line))
    width = int(PAD * 2 + COLS * CHAR_W)
    height = HEADER_H + PAD + LINE_H * len(rows) + PAD
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'font-family="{FONT}" font-size="13">',
        f"  <title>{html.escape(title, quote=False)}</title>",
        f'  <rect width="{width}" height="{height}" rx="8" fill="{COLOURS["bg"]}" stroke="{COLOURS["frame"]}"/>',
        f'  <line x1="0" y1="{HEADER_H}" x2="{width}" y2="{HEADER_H}" stroke="{COLOURS["frame"]}"/>',
        '  <circle cx="22" cy="20" r="6" fill="#ff5f57"/><circle cx="42" cy="20" r="6" fill="#febc2e"/>'
        '<circle cx="62" cy="20" r="6" fill="#28c840"/>',
        f'  <text x="{width / 2:.0f}" y="25" text-anchor="middle" fill="{COLOURS["dim"]}">'
        f"{html.escape(title, quote=False)}</text>",
    ]
    y = HEADER_H + PAD + 14
    for text, base in rows:
        out.append(f'  <text x="{PAD}" y="{y}" xml:space="preserve" fill="{base}">{spans(text, base)}</text>')
        y += LINE_H
    out.append("</svg>")
    return "\n".join(out) + "\n"


def normalise(output: str, repo: Path) -> str:
    """The repository's absolute path becomes relative: ``<repo>/.sherpa/…`` → ``.sherpa/…``, a bare one → ``.``."""
    return output.replace(str(repo) + "/", "").replace(str(repo), ".")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("source", nargs="?", default=None, help="'-' to read the output from stdin instead of running")
    ap.add_argument("--out", default=str(ROOT / "assets" / "demo.svg"))
    a = ap.parse_args(argv)
    command = "sherpa plan ."
    if a.source == "-":
        output = sys.stdin.read()
    else:
        r = subprocess.run(["sherpa", "plan", "."], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            sys.stderr.write(r.stderr)
            return r.returncode
        output = r.stdout
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    svg = render(command, normalise(output, ROOT), title=f"sherparc/Sherpa on itself — {day}")
    Path(a.out).write_text(svg, encoding="utf-8", newline="\n")
    print(f"→ {a.out} ({len(svg.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
