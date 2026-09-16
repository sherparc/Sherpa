"""sherpa — CLI entry point.

Three stages, three artefacts (see docs/plan.md):
  scan   -> .sherpa/codebase-model.json   (deterministic, no LLM)
  plan   -> .sherpa/harness-plan.yaml     (rules over the model; proposals and reasoned no's with evidence)
  apply  -> harness files + state         (deterministic, idempotent)
  status -> drift between state and file system

Exit codes: 0 ok · 1 error (git, config, plan file) · 2 command not implemented yet.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sherpa import __version__
from sherpa.gitinfo import GitError

EXIT_OK, EXIT_ERROR, EXIT_NOT_IMPLEMENTED = 0, 1, 2
MODEL_OUT = Path(".sherpa") / "codebase-model.json"
PLAN_OUT = Path(".sherpa") / "harness-plan.yaml"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sherpa", description=__doc__.split("\n")[0])
    p.add_argument("--version", action="version", version=f"sherpa {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="capture the codebase deterministically -> .sherpa/codebase-model.json")
    s.add_argument("repo", nargs="?", default=".", help="repo root (default: .)")
    s.add_argument("--trunk", help="force the trunk branch, e.g. dev (otherwise ADR-0003 / sherpa.toml)")
    s.add_argument("--no-fetch", action="store_true", help="skip 'git fetch origin' before scanning")
    s.add_argument("--as-of", help="window end (YYYY-MM-DD or ISO-8601); default: committer date of the trunk rev")
    s.add_argument("--top", type=int, help="number of hotspots (default 20 or sherpa.toml)")
    s.add_argument("--out", help=f"output file; '-' = stdout (default: <repo>/{MODEL_OUT})")

    pl = sub.add_parser("plan", help="harness proposals from the model -> .sherpa/harness-plan.yaml")
    pl.add_argument("repo", nargs="?", default=".", help="repo root (default: .)")
    pl.add_argument("--rescan", action="store_true", help="rebuild the model even if it exists")
    pl.add_argument("--no-fetch", action="store_true", help="skip 'git fetch origin' when (re)scanning")
    pl.add_argument("--out", help=f"output file; '-' = YAML to stdout (default: <repo>/{PLAN_OUT})")

    for name, help_ in (
        ("apply", "create the approved plan (idempotent, state file)"),
        ("status", "compare state with the file system"),
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
        f"{len(g.files)} files, {g.commits_90d} commits/90d, {g.commits_30d}/30d, "
        f"{len(g.hotspots)} hotspots, {len(model.modules)} modules → {out}",
        file=sys.stderr,
    )
    return EXIT_OK


def cmd_plan(args: argparse.Namespace) -> int:
    """Load the model (or scan), apply the rules, keep decisions from the previous plan, write."""
    from sherpa import config
    from sherpa import model as model_mod
    from sherpa.plan import build_plan, render_console, yamlio
    from sherpa.scan import scan

    repo = Path(args.repo).resolve()
    model_path = repo / MODEL_OUT
    model = None
    if model_path.exists() and not args.rescan:
        try:
            model = model_mod.load(model_path)
        except (ValueError, KeyError, TypeError) as e:
            print(f"sherpa plan: rebuilding the model ({e})", file=sys.stderr)
    if model is None:
        model = scan(repo, fetch=not args.no_fetch)
        model.write(model_path)
        print(f"sherpa plan: model scanned → {model_path}", file=sys.stderr)

    plan = build_plan(model, config.load(repo).plan)
    out = None if args.out == "-" else (Path(args.out) if args.out else repo / PLAN_OUT)
    previous = yamlio.load(out) if out and out.exists() else None
    plan, kept = yamlio.merge_decisions(plan, previous)

    if out is None:
        sys.stdout.write(yamlio.dumps(plan))
        sys.stderr.write(render_console(plan, "harness-plan.yaml"))
        return EXIT_OK
    yamlio.write(plan, out)
    sys.stdout.write(render_console(plan, out.name))
    tail = f" ({kept} decisions kept)" if kept else ""
    print(f"→ {out}{tail}", file=sys.stdout)
    return EXIT_OK


def _console_utf8() -> None:
    """Windows consoles and pipes are often cp1252: ✓/✗ must never crash the command."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and (stream.encoding or "").lower().replace("-", "") != "utf8":
            stream.reconfigure(errors="replace")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _console_utf8()
    try:
        if args.cmd == "scan":
            return cmd_scan(args)
        if args.cmd == "plan":
            return cmd_plan(args)
    except (GitError, ValueError, OSError) as e:
        print(f"sherpa {args.cmd}: {e}", file=sys.stderr)
        return EXIT_ERROR
    print(f"sherpa {args.cmd}: not implemented yet (see docs/plan.md, milestone table)", file=sys.stderr)
    return EXIT_NOT_IMPLEMENTED


if __name__ == "__main__":
    sys.exit(main())
