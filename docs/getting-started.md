# Getting started

Ten minutes from a clone to a harness you can read, question and commit. Everything Sherpa does is
deterministic: the same repository state gives the same model, the same plan and the same files — there is no LLM
in any of the steps below.

## 1. Install

Sherpa is a Python 3.12+ CLI with one runtime dependency (PyYAML). Release wheels come with milestone M2b; today
you install straight from the repository:

```bash
uv tool install git+https://github.com/sherparc/Sherpa.git      # or: pipx install git+https://github.com/sherparc/Sherpa.git
sherpa --version
```

Prerequisites in the target repository: `git` on the `PATH`, a remote named `origin`, and a trunk branch Sherpa
can find (`origin/HEAD`, or one of `main`, `master`, `dev`, `develop`, `trunk` — or set it in
[`sherpa.toml`](reference/configuration.md)). Sherpa measures **only** `origin/<trunk>`; your checked-out branch
and working tree are invisible to it.

## 2. Plan

```bash
cd /path/to/repo
sherpa plan
```

`plan` scans first when there is no model yet (or the trunk moved since the last scan), writes
`.sherpa/codebase-model.json`, then prints the proposals and reasoned no's and writes
`.sherpa/harness-plan.yaml`:

```console
harness-plan.yaml — 6 proposals, 4 reasoned no's
  + outcome     shop                          mandatory: no harness without an outcome signal (ADR-0008) ✓
  + owner-doc   pay                           24 commits/90d, 1 dependents ✓ · 40 files ✓
  + owner-doc   core                          1 commits/90d, 2 dependents ✓ · 3 files ✓
  + agent       pay                           rank 1/4 churn ✓ · 24 commits/90d ✓ · 40 files ✓ · 2 authors ✓
  + test-infra  suite                         26 commits/90d vs. 24 (pay) ✓
  + skill       regenerate-django-migrations  svc/pay/pay/migrations · 6 generated files, 1 configs ✓
  - owner-doc   web                           1 commits/90d, 0 dependents ✓ · 3 files ✗
  - owner-doc   old                           0 commits/90d, 0 dependents ✗ · 2 files ✗
  - librarian   pay                           rank 1/4 momentum ✓ · 24 commits/30d, 24/90d ✗
  - librarian   core                          rank 2/4 momentum ✓ · 1 commits/30d, 1/90d ✗
  1 dormant units without owner doc (0 commits/90d, 0 dependents): old — the first commit turns them into a proposal; each is listed above as a no.
  1 small units without owner doc (< 5 files, 0 dependents): web — listed above as no's; owner_doc_min_files in sherpa.toml [plan] moves the floor, a dependent overrides it.
  not listed, out of reach: 2 units for agent (rank > 1 and < 20 commits/90d), 1 for librarian (rank > 2 and below both floors).
→ .sherpa/harness-plan.yaml
```

Read it like a code review: every `+` is a proposal with its evidence, every `-` a no with the criterion that
would flip it. Nothing is created yet.

## 3. Decide

Open `.sherpa/harness-plan.yaml`. Every entry has `decision: null`. You have three choices per entry:

- leave it — proposals (`default: propose`) are applied, no's (`default: skip`) are not;
- `decision: reject` — a proposal you do not want;
- `decision: accept` — a no you want anyway.

Decisions survive the next `sherpa plan` (matched by kind, target and scope), so you can re-plan after every
merge without losing them. Thresholds too strict or too loose for your repo? Adjust `[plan]` in
[`sherpa.toml`](reference/configuration.md) and re-plan.

## 4. Apply

```bash
sherpa apply
```

Dry run first — every file with `+ new`, `~ updated`, `= unchanged` or `! skipped` and the reason — then one
question:

```console
targets: claude, agents-md · home: .agents
sherpa apply — plan origin/main@5db69c4ddd: 10 entries, 5 selected → 18 files
  + .agents/docs/modules/core.md                          owner-doc core                new
  + .agents/docs/modules/pay.md                           owner-doc pay                 new
  + .agents/docs/modules/suite.md                         test-infra suite              new
  …
  + svc/pay/CLAUDE.md                                     owner-doc pay                 new
  + tests/suite/AGENTS.md                                 test-infra suite              new
  + tests/suite/CLAUDE.md                                 test-infra suite              new
18 to add, 0 to change, 0 unchanged, 0 skipped.
apply? [y/N] y
check: 0 FAIL, 0 WARN
18 files written · harness_rev c38498363846 → .sherpa/state.json
```

The first line is the layout Sherpa resolved: owner docs and skills live under `.agents/` (the directory Codex
and the AGENTS.md family read) or `.claude/` — whichever your repo already has; Sherpa asks when it has both or
neither, `.agents` being the default — and the
files are projected for the runtimes it detected — Claude Code (`.claude/agents`, hooks, `CLAUDE.md`) and the
`AGENTS.md` family (a nested `AGENTS.md` per module, loaded by Codex, Cursor, Gemini CLI, Copilot when they work
there). Sherpa owns exactly the marked blocks inside those files (`<!-- sherpa:begin facts -->` …
`<!-- sherpa:end facts -->`) plus its own scripts; every other line is yours. Write your knowledge into the owner
docs' `structure`, `rules`, `key services` sections — the next `apply` refreshes the facts block and leaves your
text alone.

## 5. Commit

Commit `.sherpa/harness-plan.yaml`, `.sherpa/state.json`, `.agents/**`, `.claude/**` and the `AGENTS.md`/`CLAUDE.md` files. Do **not** commit
`.sherpa/codebase-model.json` (it is regenerated from the trunk) — add `.sherpa/codebase-model.json` to your
`.gitignore`. Telemetry under `.sherpa/telemetry/` ignores itself.

## 6. Keep it current

```bash
sherpa status        # what changed since the last apply: drift per file and block, checker findings, outcome labels
sherpa plan          # after merges: rescans when the trunk moved, keeps your decisions
sherpa apply         # refreshes the facts blocks; the second run in a row prints "nothing to do."
```

From the first `apply` on, every Claude Code execution in the repo gets an outcome label (`success`, `failed`,
`unknown`) stamped with the harness version, so a harness change has a number to answer to.

## Where to go next

- What every line of the plan means: [commands/plan.md](commands/plan.md) and [concepts/harness-plan.md](concepts/harness-plan.md).
- What every file under `.claude/` is for: [commands/apply.md](commands/apply.md) and [concepts/harness-apply.md](concepts/harness-apply.md).
- Every knob: [reference/configuration.md](reference/configuration.md).
