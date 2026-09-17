"""Atomic text writes for Sherpa's own artefacts (ADR-0017).

``.sherpa/state.json`` and ``harness-plan.yaml`` are indexes over the repository, not the source of truth — but a
half-written index breaks every later command. Write to a sibling temp file and ``os.replace`` it: a crash leaves
the old file intact or the new one complete, never a torn one. Harness files themselves go through ``apply``'s
write-and-roll-back path; this helper is for the index files only.
"""

from __future__ import annotations

import os
from pathlib import Path


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
