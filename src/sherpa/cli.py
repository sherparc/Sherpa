"""sherpa — CLI entry point.

Three stages, three artefacts (see docs/plan.md):
  scan   -> .sherpa/codebase-model.json   (deterministic, no LLM)
  plan   -> .sherpa/harness-plan.yaml     (rules over the model; proposals and reasoned no's with evidence)
  apply  -> .claude/** + .sherpa/state.json (dry run by default; deterministic, idempotent)
  status -> drift between state and file system, checker findings, outcome labels
  check  -> structural rules only (the same file is deployed as .claude/scripts/sherpa-check.py)
  doctor -> every prerequisite with a fix (first contact); self-update -> the next release from GitHub

Exit codes: 0 ok · 1 error (git, config, plan file, checker FAIL, doctor problem, update failed).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sherpa import __version__, update
from sherpa.gitinfo import GitError

EXIT_OK, EXIT_ERROR = 0, 1
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
    pl.add_argument(
        "--accept", action="append", default=[], metavar="KIND:TARGET[:SCOPE]", help="decide an entry (repeatable)"
    )
    pl.add_argument(
        "--reject", action="append", default=[], metavar="KIND:TARGET[:SCOPE]", help="decide an entry (repeatable)"
    )

    ap = sub.add_parser("apply", help="create the approved plan -> .claude/** and .sherpa/state.json (dry run first)")
    ap.add_argument("repo", nargs="?", default=".", help="repo root (default: .)")
    ap.add_argument("--yes", "-y", action="store_true", help="write without asking (CI)")
    ap.add_argument("--dry-run", action="store_true", help="only list the files, never ask")
    ap.add_argument("--no-check", action="store_true", help="skip the checker after writing (no rollback)")

    st = sub.add_parser("status", help="drift between state and files, checker findings, outcome labels")
    st.add_argument("repo", nargs="?", default=".", help="repo root (default: .)")
    st.add_argument("--json", action="store_true", help="the report as JSON (drift, findings, outcomes, plan)")

    ck = sub.add_parser("check", help="structural rules for .claude/** (exit 1 on FAIL)")
    ck.add_argument("repo", nargs="?", default=".", help="repo root (default: .)")
    ck.add_argument("--json", action="store_true", help="findings as JSON")
    ck.add_argument("--strict", action="store_true", help="C1–C5 FAIL in every file, not only in sherpa's (ADR-0047)")

    ad = sub.add_parser(
        "adopt", help="take an existing harness into the state without changing a byte; rebuilds a lost state"
    )
    ad.add_argument("repo", nargs="?", default=".", help="repo root (default: .)")
    ad.add_argument("--dry-run", action="store_true", help="only report, write neither state nor plan marks")

    dr = sub.add_parser("doctor", help="every prerequisite (git, origin, trunk, runtime, install, update) with a fix")
    dr.add_argument("repo", nargs="?", default=".", help="repo root (default: .)")
    dr.add_argument("--offline", action="store_true", help="skip the release check (no network)")
    dr.add_argument("--json", action="store_true", help="the checks as JSON")

    su = sub.add_parser("self-update", help="install the latest GitHub release with the installer that owns this copy")
    su.add_argument("--check", action="store_true", help="only report whether a newer release exists")
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
    plan, _, dropped_covers = yamlio.merge_covers(plan, previous, repo)
    plan.notes.extend(dropped_covers)
    plan, decided = yamlio.decide(plan, args.accept, args.reject)
    plan, covered = yamlio.mark_covered(plan, _load_state_or_empty(repo, "plan")[0], repo)

    if out is None:
        sys.stdout.write(yamlio.dumps(plan))
        sys.stderr.write(render_console(plan, "harness-plan.yaml"))
        return EXIT_OK
    yamlio.write(plan, out)
    sys.stdout.write(render_console(plan, out.name))
    counts = (("decisions kept", kept), ("decided now", decided), ("covered by existing files", covered))
    tails = [f"{n} {t}" for t, n in counts if n]
    print(f"→ {out}" + (f" ({', '.join(tails)})" if tails else ""), file=sys.stdout)
    return EXIT_OK


def _load_plan_and_model(repo: Path):
    from sherpa import model as model_mod
    from sherpa.plan import yamlio

    plan_path, model_path = repo / PLAN_OUT, repo / MODEL_OUT
    if not plan_path.exists():
        raise ValueError(f"{plan_path} not found — run `sherpa plan` first")
    if not model_path.exists():
        raise ValueError(f"{model_path} not found — run `sherpa plan` first")
    try:
        model = model_mod.load(model_path)
    except (ValueError, KeyError, TypeError) as e:  # an older sherpa's model after an upgrade: plan rescans it
        raise ValueError(f"{model_path}: {e} — run `sherpa plan` (it rescans)") from None
    return yamlio.plan_from_dict(yamlio.load(plan_path)), model


def _load_state(repo: Path):
    from sherpa.apply import state as state_mod

    path = repo / state_mod.STATE_PATH
    return state_mod.load(path) if path.exists() else state_mod.State()


def _load_state_or_empty(repo: Path, command: str):
    """``(state, error)``: the state is a rebuildable index (ADR-0017, ADR-0034), so a torn one is reported on
    stderr and treated as empty — the way out, ``sherpa adopt``, is never blocked by the very file it rebuilds."""
    from sherpa.apply import state as state_mod

    try:
        return _load_state(repo), None
    except ValueError as e:
        print(f"sherpa {command}: {e}", file=sys.stderr)
        return state_mod.State(), str(e)


ASSUMED_HOME = (
    "note: both .agents/ and .claude/ exist and nothing decides where the core lives — this preview assumes "
    '.agents; the real run asks, or set [apply] home = ".agents" or ".claude" in sherpa.toml.'
)


def _resolve_layout(repo: Path, state, *, ask: bool, preview: bool = False) -> tuple[str, tuple[str, ...], list[str]]:
    """Home and targets (ADR-0015): sherpa.toml beats the state beats detection. Both ``.agents`` and ``.claude``
    present and nothing decided yet → ask on a terminal, refuse otherwise — except a ``preview`` (dry run,
    ``status``), which assumes ``.agents`` and says so instead of stopping (ADR-0036). A target directory that is
    a repository of its own is refused — sherpa works with one repository (ADR-0045); a preview names it and
    goes on."""
    from sherpa import config
    from sherpa.apply.render import check_script

    cfg = config.load(repo).apply
    notes: list[str] = []
    has_claude = (repo / ".claude").is_dir() or (repo / "CLAUDE.md").is_file()
    has_agents = (repo / ".agents").is_dir() or (repo / "AGENTS.md").is_file()
    home = cfg.home or state.home
    if not home:
        both = (repo / ".agents").is_dir() and (repo / ".claude").is_dir()
        neither = not (repo / ".agents").is_dir() and not (repo / ".claude").is_dir()
        footprint = [h for h in config.HOMES if (repo / check_script(h)).is_file()]
        tty = ask and sys.stdin.isatty()
        if both and len(footprint) == 1:
            home = footprint[0]  # sherpa's own checker copy says where the core lives (a lost state, ADR-0017)
        elif both and preview:
            home, notes = ".agents", [ASSUMED_HOME]
        elif both and not tty:
            raise ValueError(
                "both .agents/ and .claude/ exist — where should owner docs and skills live? "
                'Set [apply] home = ".agents" or ".claude" in sherpa.toml'
            )
        elif (both or neither) and tty:
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
    targets = tuple(targets)
    nested = _nested_repositories(repo)
    if nested and not preview:
        raise ValueError(nested[0])
    notes += [f"note: {n} — this preview goes on; `apply` and `adopt` refuse." for n in nested]
    return home, targets, notes


def _nested_repositories(repo: Path) -> list[str]:
    """Sherpa works with one repository (ADR-0045): a directory in the tree that is a repository of its own — a
    submodule, a clone, a harness checked out under ``.claude/`` — is where ``apply`` would write files another
    repository tracks and ``adopt`` would read files that are not this repository's harness. One line, the
    refusal's text, naming up to five of them."""
    from sherpa import gitinfo

    nested = gitinfo.nested_repositories(repo)
    if not nested:
        return []
    shown = ", ".join(f"{d}/" for d in nested[:5]) + (f" and {len(nested) - 5} more" if len(nested) > 5 else "")
    what = "is a repository of its own" if len(nested) == 1 else "are repositories of their own"
    return [
        f"{shown} {what} ({nested[0]}/.git) — sherpa works with one repository: move the clone out of the tree, "
        "or run sherpa in that repository"
    ]


def cmd_apply(args: argparse.Namespace) -> int:
    """Dry run always; then ask (or ``--yes``), write, check, roll back on new FAILs, write the state."""
    from sherpa import apply

    repo = Path(args.repo).resolve()
    plan, model = _load_plan_and_model(repo)
    _refuse_stale(repo, plan)
    state = _load_state(repo)
    home, targets, notes = _resolve_layout(repo, state, ask=not args.yes and not args.dry_run, preview=args.dry_run)
    actions = apply.plan_files(apply.targets_for(plan, model, home=home, targets=targets), repo, state)
    sys.stdout.write(f"targets: {', '.join(targets)} · home: {home}\n")
    for note in notes:
        print(note, file=sys.stdout)
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


def _stale(repo: Path, plan) -> tuple[str, str, str] | None:
    """``(trunk, plan rev, current rev)`` when the trunk moved since the plan was made, else None (no fetch here)."""
    from sherpa import gitinfo

    trunk, rev = plan.model.get("trunk", ""), plan.model.get("rev", "")
    if trunk and gitinfo.ref_exists(repo, trunk) and (now := gitinfo.rev(repo, trunk)) != rev:
        return trunk, rev, now
    return None


def _refuse_stale(repo: Path, plan) -> None:
    """Like a saved Terraform plan: the trunk moved since the plan was made → plan again."""
    if s := _stale(repo, plan):
        trunk, rev, now = s
        raise ValueError(
            f"harness-plan.yaml is from {trunk}@{rev[:10]}, {trunk} is now at {now[:10]} — run `sherpa plan` first"
        )


def cmd_status(args: argparse.Namespace) -> int:
    """What ``apply`` would do now (drift), checker findings, and the outcome labels per harness_rev."""
    from sherpa import apply
    from sherpa.apply import status as status_mod

    repo = Path(args.repo).resolve()
    state, state_error = _load_state_or_empty(repo, "status")
    plan, model = _load_plan_and_model(repo)
    home, targets, _ = _resolve_layout(repo, state, ask=False, preview=True)
    actions = apply.plan_files(apply.targets_for(plan, model, home=home, targets=targets), repo, state)
    report = status_mod.report(repo, state, actions, stale=_stale(repo, plan), state_error=state_error)
    sys.stdout.write(status_mod.render_json(report) if args.json else status_mod.render(report))
    return EXIT_ERROR if report.fails else EXIT_OK


def cmd_adopt(args: argparse.Namespace) -> int:
    """Inventory, reconcile against the plan's rendering, link to units, write the state and the plan's covered
    marks. Nothing under the harness changes (ADR-0007); a torn state is rebuilt from the files (ADR-0017). A stale
    plan is no reason to refuse: ``adopt`` imports what is there, like ``terraform import`` (ADR-0034)."""
    from sherpa import apply
    from sherpa.apply import adopt as adopt_mod
    from sherpa.apply import state as state_mod
    from sherpa.plan import yamlio

    repo = Path(args.repo).resolve()
    plan, model = _load_plan_and_model(repo)
    state, _ = _load_state_or_empty(repo, "adopt")
    home, targets, notes = _resolve_layout(repo, state, ask=not args.dry_run, preview=args.dry_run)
    rendered = apply.targets_for(plan, model, home=home, targets=targets)
    a = adopt_mod.adopt(repo, plan, rendered, state, home=home, runtime_targets=targets)
    sys.stdout.write(adopt_mod.render(a, home=home, targets=targets))
    for note in notes:
        print(note, file=sys.stdout)
    new_state = adopt_mod.new_state(a, plan, state, home=home, targets=targets)
    if args.dry_run:
        print(f"dry run: {a.counts()} · harness_rev {new_state.harness_rev} (state not written)", file=sys.stdout)
        return EXIT_OK
    if not a.files and not state.files:
        print("nothing to adopt — no harness files here; `sherpa apply` creates one.", file=sys.stdout)
        return EXIT_OK
    new_state.write(repo / state_mod.STATE_PATH)
    plan, covered = yamlio.mark_covered(plan, new_state, repo)
    yamlio.write(plan, repo / PLAN_OUT)
    print(
        f"state: {a.counts()} · harness_rev {new_state.harness_rev} → {state_mod.STATE_PATH.as_posix()} · "
        f"{covered} plan entries covered → {PLAN_OUT.as_posix()}",
        file=sys.stdout,
    )
    return EXIT_OK


def cmd_check(args: argparse.Namespace) -> int:
    from sherpa import check

    return check.main([args.repo] + (["--json"] if args.json else []) + (["--strict"] if args.strict else []))


def cmd_doctor(args: argparse.Namespace) -> int:
    from sherpa import doctor

    checks = doctor.run(Path(args.repo).resolve(), network=not args.offline)
    sys.stdout.write(doctor.render_json(checks) if args.json else doctor.render(checks))
    return EXIT_ERROR if any(c.level == "fail" for c in checks) else EXIT_OK


def cmd_self_update(args: argparse.Namespace) -> int:
    return update.self_update(check_only=args.check)


def _console_utf8() -> None:
    """Windows consoles and pipes are often cp1252: ✓/✗ must never crash the command."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and (stream.encoding or "").lower().replace("-", "") != "utf8":
            stream.reconfigure(errors="replace")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _console_utf8()
    update.start_check(args.cmd)  # daily, in the background; the hint below reads only what is cached
    try:
        code = _dispatch(args)
    except (GitError, ValueError, OSError, update.UpdateError) as e:
        print(f"sherpa {args.cmd}: {e}", file=sys.stderr)
        return EXIT_ERROR
    if line := update.hint(args.cmd):
        print(line, file=sys.stderr)
    return code


def _dispatch(args: argparse.Namespace) -> int:
    if True:
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
        if args.cmd == "adopt":
            return cmd_adopt(args)
        if args.cmd == "doctor":
            return cmd_doctor(args)
        if args.cmd == "self-update":
            return cmd_self_update(args)
    raise ValueError("unknown command")  # argparse refuses unknown commands before we get here


if __name__ == "__main__":
    sys.exit(main())
