# ADRs — Architecture Decision Records

One file per decision: context → decision → reasoning → consequences. Never edited, only superseded by a new ADR
(`Status: superseded by ADR-xxxx`). After **every** iteration the decisions taken are recorded here — what has
no ADR is not decided.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-language-python.md) | Python, stdlib-first; Rust only on a flip criterion | accepted |
| [0002](0002-generic-vs-specific.md) | Separation generic (template) / adapter / project-only | proposed |
| [0003](0003-trunk-detection.md) | Scan always against `origin/<trunk>`; detection order | accepted |
| [0004](0004-model-providers.md) | Own thin provider layer; no LangChain/LangGraph | accepted |
| [0005](0005-plan-format-and-check-in.md) | Plan as YAML; plan + state checked in, model not | accepted |
| [0006](0006-relative-thresholds-with-floor.md) | Thresholds relative (percentile) with an absolute floor | accepted |
| [0007](0007-adopt-not-overwrite.md) | `sherpa adopt` takes over existing harnesses, never overwrites | accepted |
| [0008](0008-dry-run-default-and-outcome-minimum.md) | `apply`: dry run first; outcome minimum in every `apply` | accepted |
| [0009](0009-namespaces-and-branch-protection.md) | Product/CLI `sherpa`, package `sherpa-harness`, org `sherparc`; `main` only via PR, pre-push hook instead of rulesets | accepted |
| [0010](0010-two-stage-licensing.md) | Two-stage licensing: proprietary now, PolyForm Small Business at release; output belongs to the user | accepted |
| [0011](0011-generated-code-is-regenerated-not-explained.md) | Generated code is regenerated, not explained: generator families in the scanner, skill instead of agent | accepted |
| [0012](0012-plan-units-visibility-decisions.md) | Plan units (modules + directories), dormant = visible no, author floor, no's only within reach, `decision` survives re-plan | accepted |
| [0013](0013-managed-blocks-and-single-source-checker.md) | `apply` owns marked blocks, not files; one checker source deployed as a delegating copy; rollback only on new FAILs; Terraform-style selection | accepted |
| [0014](0014-owner-doc-floor-by-files.md) | Owner docs need ≥ 5 files unless something depends on the unit; small units listed as no's | accepted |
| [0015](0015-target-layer-neutral-core.md) | Runtime-neutral core under `.agents`/`.claude` (`home`), adapters per target (`claude`, `agents-md`), nested AGENTS.md/CLAUDE.md per unit, ask when both homes exist | accepted |
| [0016](0016-never-overwrite-only-add.md) | In the user's repository Sherpa never overwrites what exists — it creates, appends, merges, and rewrites only its own unchanged bytes | accepted |
| [0017](0017-state-is-a-rebuildable-index.md) | The state is a rebuildable index over the harness files: atomic writes, `adopt` rebuilds a lost or torn state, readers name the way out | accepted |
| [0018](0018-distribution-github-releases.md) | Distribution through GitHub Releases: wheel per tag, `self-update` via the owning installer, a daily hint that never blocks, `doctor` first | accepted |
| [0019](0019-stamp-without-rev.md) | The facts stamp carries the window end only; the rev lives in the state and the plan header (M3d) | accepted |
| [0020](0020-sub-units-for-single-manifest-repos.md) | Sub-units for single-manifest repositories by a depth rule, `[plan] units` overrides it (M3d) | accepted |
| [0021](0021-change-coupling-with-size-cap.md) | Change coupling per module with floors, measured only on commits below a size cap (max(5, half the modules)); the model records what it skipped | accepted |
| [0022](0022-adopt-recognises-older-renderings.md) | `adopt` recognises older stamp formats as sherpa's rendering (`LEGACY_STAMPS`), so a rebuilt state after an upgrade keeps ownership | accepted |
| [0023](0023-hermes-target.md) | Hermes Agent as the third target (thin adapter on `agents-md`, `version` in skill front matter, hook wiring as a `doctor` check); independence through open runtimes before any runtime of Sherpa's own | accepted |
| [0024](0024-runtime-plugins.md) | Runtime plugins (M7a): a Claude Code plugin and a Hermes bundle from one source, thin — commands call the CLI, the hook stays with `apply` | accepted |
| [0025](0025-manifest-tie-break-by-language-share.md) | Two manifests in one directory: the kind with more source files under it wins, a tie by manifest name | accepted |
| [0026](0026-coupling-excludes-the-root-module.md) | Change coupling leaves out the root module next to other modules (a catch-all is not a unit); `coupling.excluded` records it | accepted |
| [0027](0027-sub-units-for-a-dominant-root-module.md) | The depth rule also runs on a root module holding ≥ `root_share` (0.5) of the files next to other modules | accepted |
| [0028](0028-outcome-evaluation-needs-a-denominator.md) | Outcome evaluation (M5) shows `n` and the `unknown` share per revision; a comparison only from 30 labelled executions per revision | accepted |
| [0029](0029-proximity-file-budget.md) | C7 budgets for proximity files: nested `CLAUDE.md`/`AGENTS.md` ≤ 8 KiB, root ≤ 32 KiB (Hermes' ceiling) | accepted |
| [0030](0030-write-compares-before-it-swaps.md) | `apply` re-reads each file before writing and skips one that changed since the preview (`changed since the preview`); no lock file | accepted |
| [0031](0031-never-write-through-a-symlink.md) | `apply` never writes through a symlink, in or out of the repository (`symlink in the path — never written through`), as `git apply` does | accepted |
| [0032](0032-atomic-file-writes-and-rollback-on-error.md) | Harness files are written whole or not at all (`sherpa.atomic`), and an `OSError` half-way rolls the written files back and names what a failed rollback left | accepted |
| [0033](0033-differing-base-files-are-yours-after-adopt.md) | A base file (checker copy, hook, ignore file) that differs from sherpa's copy is yours after `adopt` and listed as a gap with the way to a fresh one — amends ADR-0017 §2 | accepted |
| [0034](0034-adopt-ignores-a-stale-plan.md) | `adopt` ignores a stale plan (`terraform import` needs the resource, not a fresh plan) and `plan`, `status`, `adopt` run on a torn state with the way out on stderr — only `apply` refuses both; amends ADR-0017/0019 | accepted |
| [0035](0035-self-update-without-a-token-uses-git-ls-remote.md) | `self-update` without a token finds the newest tag with `git ls-remote` (https, then ssh, never prompting) and saves the wheel under its PEP 427 name; pip, not a mock, is the bar — amends ADR-0018 §2 | accepted |
| [0036](0036-a-preview-assumes-a-home-instead-of-refusing.md) | With both homes present and nothing decided, `apply --dry-run`, `adopt --dry-run` and `status` assume `.agents` and say so; a write still asks or refuses — amends ADR-0015 for read-only runs | accepted |
| [0037](0037-a-nested-repository-under-a-target-directory-is-named.md) | ~~A home or `.claude/` that is a repository of its own (`.git` inside) is named with one note in the preview and the write — never refused, never skipped~~ | superseded by ADR-0045 |
| [0042](0042-stdlib-schema-validator.md) | `sherpa/schema.py` validates the shipped schemas with the stdlib on every reader, in production as in the tests; `jsonschema` stays a dev extra as the reference on one input matrix — amends ADR-0005 | accepted |
| [0043](0043-ci-minutes-follow-the-event.md) | CI matrix by event — Linux per pull request, Linux + Windows on `main`, macOS weekly, all three on a manual run; docs-only changes skip CI, newer pushes cancel older runs, every job has a timeout | accepted |
| [0044](0044-ci-files-by-directory.md) | A YAML file under `pipelines/`, `.pipelines/`, `.azure-pipelines/` or `.azuredevops/` is a CI definition: Azure DevOps fixes no file name, so the directory carries the convention | accepted |
| [0045](0045-one-repository.md) | Sherpa works with one repository: a nested repository anywhere in the tree (a harness clone under `.claude/`, a submodule, a vendored clone) stops `apply` and `adopt` with the way out named; the dry runs go on with a note — supersedes ADR-0037 | accepted |
| [0046](0046-the-cover-is-the-teams-decision.md) | `covered:` written by hand is a decision: kept across re-plans, honoured by `adopt` first; only `docs/modules/` links, one file per entry, ties cover nothing and are named — amends ADR-0007 | accepted |
| [0047](0047-checker-fails-only-in-managed-files.md) | C1–C5 FAIL only in files sherpa generated, WARN `(yours)` in adopted and unrecorded ones; `--strict` for all, strict without a state; `apply` counts what it writes as managed — amends ADR-0032 | accepted |
| [0048](0048-apply-takes-its-own-bytes-back.md) | `apply` takes back what it wrote and nobody changed — a rejected entry's or a vanished unit's files, blocks and hook groups; `--remove` is the uninstall that leaves `git status --ignored` as before the first apply; a seeded blocks file remembers it was sherpa's whole; `adopt` records its own leftovers as generated, never as covers — amends ADR-0016, 0013, 0007, 0032 | accepted |
| [0050](0050-host-breadth-one-thin-adapter-per-runtime.md) | Host breadth is a goal of its own (M3k): one thin adapter per agent runtime — detection in `doctor`, the host's native rule file where it has one, the outcome hook where it has hooks — on top of `agents-md` like `hermes`; the gate "a corpus repository uses it" is dropped — amends ADR-0015 §2, ADR-0023, plan Q8 | accepted |
| [0038](0038-git-paths-nul-separated.md) | `git log` is read with `-z` like `ls-tree`, so a path with an umlaut, a tab or a newline keeps its churn; a newline path gets no LOC instead of shifting `cat-file` answers | accepted |
| [0039](0039-coupling-carries-its-denominator.md) | `Coupling.of` — the row prints the denominator the share was computed with (`6 of 12 measured commits, 50 %`); model schema v5 — amends ADR-0021 §4 | accepted |
| [0040](0040-test-runs-are-command-words.md) | The outcome hook counts a test run only when a runner is the command word of a shell segment, and stamps the `harness_rev` the execution started with (`harness_rev_at_stop` when it changed) — amends ADR-0008/0028 | accepted |
| [0041](0041-architecture-diagrams-as-mermaid.md) | Architecture diagrams as Mermaid text under `docs/architecture/` — one page per mechanism with its owner named, projected into the vault, checked by a stdlib test, never rendered by a tool — decides plan Q25's documentation half | accepted |
