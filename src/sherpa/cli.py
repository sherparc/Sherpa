"""sherpa — CLI entry point.

Three stages, three artefacts (see docs/plan.md):
  scan   -> .sherpa/codebase-model.json   (deterministic, no LLM)
  plan   -> .sherpa/harness-plan.yaml     (rules over the model; proposals and reasoned no's with evidence)
  apply  -> .claude/** + .sherpa/state.json (dry run by default; deterministic, idempotent)
  status -> drift between state and file system, checker findings, outcome labels
  check  -> structural rules only (the same file is deployed as .claude/scripts/sherpa-check.py)

Exit codes: 0 ok · 1 error (git, config, plan file, checker FAIL) · 2 command not implemented yet.
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

    ap = sub.add_parser("apply", help="create the approved plan -> .claude/** and .sherpa/state.json (dry run first)")
    ap.add_argument("repo", nargs="?", default=".", help="repo root (default: .)")
    ap.add_argument("--yes", "-y", action="store_true", help="write without asking (CI)")
    ap.add_argument("--dry-run", action="store_true", help="only list the files, never ask")
    ap.add_argument("--no-check", action="store_true", help="skip the checker after writing (no rollback)")

    st = sub.add_parser("status", help="drift between state and files, checker findings, outcome labels")
    st.add_argument("repo", nargs="?", default=".", help="repo root (default: .)")

    ck = sub.add_parser("check", help="structural rules for .claude/** (exit 1 on FAIL)")
    ck.add_argument("repo", nargs="?", default=".", help="repo root (default: .)")
    ck.add_argument("--json", action="store_true", help="findings as JSON")

    sub.add_parser("adopt", help="take over an existing harness into the state (M3, not implemented yet)").add_argument(
        "repo", nargs="?", default="."
    )
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
    from sherpa import config, gitinfo
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
    if model is not None and not args.no_fetch:
        gitinfo.fetch_origin(repo)
    if model is not None and gitinfo.rev(repo, model.git.trunk.ref) != model.git.trunk.rev:
        print(f"sherpa plan: {model.git.trunk.ref} moved since the last scan — rescanning", file=sys.stderr)
        model = None
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


def _load_plan_and_model(repo: Path):
    from sherpa import model as model_mod
    from sherpa.plan import yamlio

    plan_path, model_path = repo / PLAN_OUT, repo / MODEL_OUT
    if not plan_path.exists():
        raise ValueError(f"{plan_path} not found — run `sherpa plan` first")
    if not model_path.exists():
        raise ValueError(f"{model_path} not found — run `sherpa plan` first")
    return yamlio.plan_from_dict(yamlio.load(plan_path)), model_mod.load(model_path)


def _load_state(repo: Path):
    from sherpa.apply import state as state_mod

    path = repo / state_mod.STATE_PATH
    return state_mod.load(path) if path.exists() else state_mod.State()


def _resolve_layout(repo: Path, state, *, ask: bool) -> tuple[str, tuple[str, ...]]:
    """Home and targets (ADR-0015): sherpa.toml beats the state beats detection. Both ``.agents`` and ``.claude``
    present and nothing decided yet → ask on a terminal, refuse otherwise."""
    from sherpa import config

    cfg = config.load(repo).apply
    has_claude = (repo / ".claude").is_dir() or (repo / "CLAUDE.md").is_file()
    has_agents = (repo / ".agents").is_dir() or (repo / "AGENTS.md").is_file()
    home = cfg.home or state.home
    if not home:
        both = (repo / ".agents").is_dir() and (repo / ".claude").is_dir()
        neither = not (repo / ".agents").is_dir() and not (repo / ".claude").is_dir()
        if both and not (ask and sys.stdin.isatty()):
            raise ValueError(
                "both .agents/ and .claude/ exist — where should owner docs and skills live? "
                'Set [apply] home = ".agents" or ".claude" in sherpa.toml'
            )
        if (both or neither) and ask and sys.stdin.isatty():
            what = "both .agents/ and .claude/ exist" if both else "no harness directory yet"
            answer = input(f"{what} — owner docs and skills under [1] .agents (default, cross-tool)  [2] .claude ? ")
            home = ".claude" if answer.strip() in ("2", ".claude") else ".agents"
        elif (repo / ".claude").is_dir():
            home = ".claude"
        else:
            home = ".agents"  # the cross-tool default, also without a terminal
    targets = cfg.targets or state.targets
    if not targets:
        detected = tuple(t for t, on in (("claude", has_claude), ("agents-md", has_agents)) if on)
        targets = detected or config.TARGETS
    return home, tuple(targets)


def cmd_apply(args: argparse.Namespace) -> int:
    """Dry run always; then ask (or ``--yes``), write, check, roll back on new FAILs, write the state."""
    from sherpa import apply

    repo = Path(args.repo).resolve()
    plan, model = _load_plan_and_model(repo)
    _refuse_stale(repo, plan)
    state = _load_state(repo)
    home, targets = _resolve_layout(repo, state, ask=not args.yes and not args.dry_run)
    actions = apply.plan_files(apply.targets_for(plan, model, home=home, targets=targets), repo, state)
    sys.stdout.write(f"targets: {', '.join(targets)} · home: {home}\n")
    if "claude" not in targets:
        print(
            "note: no target with hooks (claude) — outcome labels are not collected (ADR-0008); "
            "add it to [apply] targets in sherpa.toml when Claude Code is used here.",
            file=sys.stdout,
        )
    sys.stdout.write(apply.render_actions(actions, plan))
    if not any(a.new is not None for a in actions):
        print("nothing to do.", file=sys.stdout)
        return EXIT_OK
    if args.dry_run:
        return EXIT_OK
    if not args.yes:
        if not sys.stdin.isatty():
            print("dry run only — pass --yes to write (no terminal to ask).", file=sys.stdout)
            return EXIT_OK
        answer = input("apply? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("aborted, nothing written.", file=sys.stdout)
            return EXIT_OK
    result = apply.write(actions, repo, state, plan, check=not args.no_check, home=home, targets=targets)
    sys.stdout.write(apply.render_result(result))
    return EXIT_ERROR if result.rolled_back else EXIT_OK


def _refuse_stale(repo: Path, plan) -> None:
    """Like a saved Terraform plan: the trunk moved since the plan was made → plan again (no fetch here)."""
    from sherpa import gitinfo

    trunk, rev = plan.model.get("trunk", ""), plan.model.get("rev", "")
    if trunk and gitinfo.ref_exists(repo, trunk) and (now := gitinfo.rev(repo, trunk)) != rev:
        raise ValueError(
            f"harness-plan.yaml is from {trunk}@{rev[:10]}, {trunk} is now at {now[:10]} — run `sherpa plan` first"
        )


def cmd_status(args: argparse.Namespace) -> int:
    """What ``apply`` would do now (drift), checker findings, and the outcome labels per harness_rev."""
    from sherpa import apply
    from sherpa.apply import status as status_mod

    repo = Path(args.repo).resolve()
    state = _load_state(repo)
    plan, model = _load_plan_and_model(repo)
    home, targets = _resolve_layout(repo, state, ask=False)
    actions = apply.plan_files(apply.targets_for(plan, model, home=home, targets=targets), repo, state)
    report = status_mod.report(repo, state, actions)
    sys.stdout.write(status_mod.render(report))
    return EXIT_ERROR if report.fails else EXIT_OK


def cmd_check(args: argparse.Namespace) -> int:
    from sherpa import check

    return check.main([args.repo] + (["--json"] if args.json else []))


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
        if args.cmd == "apply":
            return cmd_apply(args)
        if args.cmd == "status":
            return cmd_status(args)
        if args.cmd == "check":
            return cmd_check(args)
    except (GitError, ValueError, OSError) as e:
        print(f"sherpa {args.cmd}: {e}", file=sys.stderr)
        return EXIT_ERROR
    print(f"sherpa {args.cmd}: not implemented yet (see docs/plan.md, milestone table)", file=sys.stderr)
    return EXIT_NOT_IMPLEMENTED


if __name__ == "__main__":
    sys.exit(main())
