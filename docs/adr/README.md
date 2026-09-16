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
