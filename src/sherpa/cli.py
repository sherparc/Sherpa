"""sherpa — CLI-Einstieg.

Drei Stufen, drei Artefakte (siehe docs/plan.md):
  scan   -> .sherpa/codebase-model.json   (deterministisch, kein LLM)
  plan   -> harness-plan                  (Wissensarchitekt; Vorschläge mit Evidenz)
  apply  -> Harness-Dateien + State       (deterministisch, idempotent)
  status -> Drift zwischen State und Dateisystem

Exit-Codes: 0 ok · 1 Fehler (Git, Konfig) · 2 Kommando noch nicht implementiert.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sherpa import __version__
from sherpa.gitinfo import GitError

EXIT_OK, EXIT_ERROR, EXIT_NOT_IMPLEMENTED = 0, 1, 2
MODEL_OUT = Path(".sherpa") / "codebase-model.json"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sherpa", description=__doc__.split("\n")[0])
    p.add_argument("--version", action="version", version=f"sherpa {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="Codebase deterministisch erfassen -> .sherpa/codebase-model.json")
    s.add_argument("repo", nargs="?", default=".", help="Repo-Wurzel (Default: .)")
    s.add_argument("--trunk", help="Trunk-Branch erzwingen, z. B. dev (sonst ADR-0003 / sherpa.toml)")
    s.add_argument("--no-fetch", action="store_true", help="kein 'git fetch origin' vor dem Scan")
    s.add_argument("--as-of", help="Fensterende (YYYY-MM-DD oder ISO-8601); Default: Committer-Datum des Trunk-Revs")
    s.add_argument("--top", type=int, help="Anzahl Hotspots (Default 20 oder sherpa.toml)")
    s.add_argument("--out", help=f"Zieldatei; '-' = stdout (Default: <repo>/{MODEL_OUT})")

    for name, help_ in (
        ("plan", "Harness-Vorschläge aus dem Modell"),
        ("apply", "Freigegebenen Plan anlegen (idempotent, State-Datei)"),
        ("status", "State vs. Dateisystem vergleichen"),
    ):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("repo", nargs="?", default=".")
    return p


def cmd_scan(args: argparse.Namespace) -> int:
    from sherpa.model import validate
    from sherpa.scan import parse_as_of, scan

    repo = Path(args.repo)
    model = scan(
        repo,
        trunk=args.trunk,
        fetch=not args.no_fetch,
        as_of=parse_as_of(args.as_of) if args.as_of else None,
        hotspots=args.top,
    )
    from dataclasses import asdict

    validate(asdict(model))
    g = model.git
    if args.out == "-":
        sys.stdout.write(model.to_json())
        return EXIT_OK
    out = Path(args.out) if args.out else repo.resolve() / MODEL_OUT
    model.write(out)
    print(
        f"sherpa scan: {model.repo} @ {g.trunk.ref} {g.trunk.rev[:10]} ({g.trunk.source}) — "
        f"{len(g.files)} Dateien, {g.commits_90d} Commits/90d, {g.commits_30d}/30d, "
        f"{len(g.hotspots)} Hotspots, {len(model.modules)} Module → {out}",
        file=sys.stderr,
    )
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "scan":
            return cmd_scan(args)
    except (GitError, ValueError, OSError) as e:
        print(f"sherpa {args.cmd}: {e}", file=sys.stderr)
        return EXIT_ERROR
    print(f"sherpa {args.cmd}: noch nicht implementiert (siehe docs/plan.md, Meilenstein-Tabelle)", file=sys.stderr)
    return EXIT_NOT_IMPLEMENTED


if __name__ == "__main__":
    sys.exit(main())
