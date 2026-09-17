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
