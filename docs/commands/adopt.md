# `sherpa adopt`

Take an existing harness into the state without changing a byte of it — and rebuild a lost or torn state from
the files. The model is `terraform import`: what is already there becomes known to Sherpa, `apply` never touches
it, and a plan entry that an existing file already fills is marked **covered** instead of being created twice.
Deterministic, no LLM, seconds.

## Synopsis

```
sherpa adopt [REPO] [--dry-run]
```

## When to run it

| Situation | What adopt does |
|---|---|
| The repository already has `.claude/`, `.agents/` or an `AGENTS.md` hierarchy | every file is recorded as `origin: adopted`; agents and owner docs are linked to the units of the plan and cover their entries; gaps are listed |
| `.sherpa/state.json` is missing, torn (a crash mid-write) or from a foreign schema | the state is rebuilt from the harness files: everything that equals the plan's rendering is sherpa's again, the rest is yours |
| Sherpa's files were copied into another clone without the state | same as above |
| A file was deleted by hand and the state still lists it | the record is dropped (reported) |

`apply` and `status` point here whenever they meet a file without a state record.

## What it does

1. **Inventory.** Every file under `.claude/` and `.agents/`, every `CLAUDE.md` and `AGENTS.md` in the tree (root
   and nested), plus sherpa's own files outside the homes (`.sherpa/telemetry/.gitignore`). Git-ignored files
   (`.claude/settings.local.json`, a private `memory/`) are not the harness and are skipped. Each file gets a
   **kind** from its path alone — never guessed from its content:

   | Kind | Path |
   |---|---|
   | `root` / `nested` | `CLAUDE.md`, `AGENTS.md` at the root / in a subdirectory |
   | `agent` | `.claude/agents/*.md` |
   | `skill` | `SKILL.md` under a `skills/` directory of either home |
   | `command` | `.claude/commands/*.md` |
   | `doc` | `<home>/docs/**/*.md` |
   | `hook` / `settings` / `script` / `eval` | `.claude/hooks/*`, `.claude/settings.json`, `<home>/scripts/*`, `<home>/evals/**` |
   | `unknown` | everything else — recorded as yours and listed with `?` |

2. **Reconcile against the plan.** Where the plan renders a file at the same path, the file is compared with the
   rendering. The state records only what it can prove:

   | The file | Recorded as |
   |---|---|
   | equals the rendering byte for byte | `generated`, whole file — sherpa's, as if `apply` had just written it |
   | has sherpa markers; a block equals its rendering | `generated`, that block's hash — `apply` keeps it current |
   | has sherpa markers; a block equals its rendering except for an **older stamp format** (`origin/main@<rev>, as of <date>` from sherpa ≤ 0.5.0) | `generated`, the hash of the bytes on disk — sherpa's rendering of its day (ADR-0022); the next `apply` rewrites it in the current form (`~ block facts updated`) |
   | has sherpa markers; a block differs otherwise | that block is **not** recorded: a hand edit stays as it is; the console says `block facts differs (hand edit) — stays` |
   | is a base file sherpa names itself (`sherpa-check.py`, `sherpa-outcome.py`, the telemetry ignore file) and differs | `generated` with the current hash — sherpa's by name; the next `apply` refreshes it (`~ updated`) |
   | is at sherpa's path for a plan entry and differs, no markers | `adopted`, linked to that entry — **covers** it |
   | is a root or nested `CLAUDE.md`/`AGENTS.md` without markers, or `settings.json` without the hook | not recorded — `apply` may still append its block or merge the hook (ADR-0016) |

3. **Link.** An adopted agent or doc elsewhere is linked to a unit of the plan, in this order: the file stem (or
   the skill directory) equals the unit's slug → *name matches*; the front matter `name` does → *front matter
   name matches*; otherwise the unit whose repository path the file mentions most often, at least twice and
   unambiguously (a deeper unit wins over its parent) → *mentions svc/pay 6×*. Anything else: *no unit matches*
   or *ambiguous: …* — listed, not guessed. A linked agent covers the unit's `agent` entry, a linked doc its
   `owner-doc` (or `test-infra`) entry.

4. **Gaps** — what an analysis by hand would find, from the same inventory:
   - an agent over the size budget (150 lines) without a `knowledge` manifest — rotation candidate;
   - a doc under `docs/` that matches no unit — moved, renamed or not a module doc;
   - an agent for a unit the plan proposes none for (below the threshold) — yours, noted;
   - proposed owner docs with no existing doc (`apply` creates them);
   - files of unknown kind.

5. **Write.** `.sherpa/state.json` (atomically, ADR-0017) and the `covered` marks in `.sherpa/harness-plan.yaml`
   (decisions untouched). Nothing under the harness changes; `git status` shows only `.sherpa/`.

## Output

```console
$ sherpa adopt .
sherpa adopt — home .claude · targets claude: 7 harness files
  a .claude/agents/ops.md           agent    no unit matches
  a .claude/agents/pay-expert.md    agent    → agent pay (mentions svc/pay 170×)
  a .claude/commands/deploy.md      command  yours
  a .claude/docs/modules/legacy.md  doc      no unit matches
  a .claude/docs/modules/pay.md     doc      at sherpa's path, yours — covers the entry
  ? .claude/notes.txt               unknown  yours
  · CLAUDE.md                       root     no sherpa markers — `apply` appends its block (ADR-0016)
gaps:
  - .claude/agents/pay-expert.md: 175 lines, no knowledge manifest — rotation candidate, facts belong in an owner doc
  - .claude/docs/modules/legacy.md: no unit matches by name or path mentions — moved, renamed or not a module doc
  - 2 proposed owner docs without an existing doc — `apply` creates them
  - 1 file of unknown kind — recorded as yours, listed above with `?`
state: 6 adopted, 0 rebuilt, 0 kept, 0 dropped · harness_rev 0d2bdd9cfe6a → .sherpa/state.json · 2 plan entries covered → .sherpa/harness-plan.yaml
```

| Mark | Meaning |
|---|---|
| `a` | adopted — yours; `apply` never touches it, `status` never reports it as drift |
| `=` | sherpa's — kept (hashes still match the previous state) or rebuilt from the rendering |
| `·` | not recorded — `apply` may still add to this file |
| `?` | unknown kind — adopted like everything else, named so you can move or delete it |

Rebuilding a lost state after an `apply`:

```console
$ rm .sherpa/state.json            # or: a crash left it half-written
$ sherpa status .
sherpa status: .sherpa/state.json is unreadable (…) — `sherpa adopt` rebuilds it from the harness files
$ sherpa adopt .
sherpa adopt — home .agents · targets claude, agents-md: 18 harness files
  = .agents/docs/modules/core.md   doc     1 of 1 blocks match the plan
  …
state: 0 adopted, 18 rebuilt, 0 kept, 0 dropped · harness_rev 2f81f4dcc00e → .sherpa/state.json · 0 plan entries covered → .sherpa/harness-plan.yaml
$ sherpa apply . --dry-run
nothing to do.
```

The rebuilt `harness_rev` is the one `apply` wrote — the state is an index over the files, and the files were
never lost. With both `.agents/` and `.claude/` present and no state to say where the core lives, the checker
copy `<home>/scripts/sherpa-check.py` answers the question; only when that is missing too does adopt ask.

## After adopt

```console
$ sherpa plan .
  + owner-doc   pay   24 commits/90d, 1 dependents ✓ · 40 files ✓ [covered by .claude/docs/modules/pay.md]
  + agent       pay   rank 1/4 churn ✓ · … [covered by .claude/agents/pay-expert.md]
→ .sherpa/harness-plan.yaml (2 covered by adopted files)
$ sherpa apply .
```

`apply` renders nothing for a covered entry; agents and proximity files of that unit point at the adopted owner
doc instead of a generated one, and the nested `CLAUDE.md`/`AGENTS.md` still carry the measured facts. To get
sherpa's version anyway, set `decision: accept` on the covered entry — a second agent for the same unit is a
decision, never a default. `sherpa status` adds `note: N adopted files are yours and never touched`; a hand edit
to an adopted file is not drift and not a C8 finding; only a deleted one is listed (`-`), and the next `adopt`
drops its record.

Adopted files are part of the harness the runtime sees, so their hashes count towards `harness_rev`; the hash of
an adopted file is refreshed by the next `adopt` (not by `apply`), and the outcome labels move to the new
revision from then on.

## Options

| Option | Effect |
|---|---|
| `REPO` | repository root (default `.`) |
| `--dry-run` | print the inventory, links and gaps; write neither state nor plan marks |

Home and targets are resolved as for [`sherpa apply`](apply.md) (`sherpa.toml [apply]`, then the state, then
the repository; a question on a terminal when both homes exist and nothing decides it).

## Exit codes

| Exit | When |
|---|---|
| 0 | done, including `--dry-run` and "nothing to adopt" (no harness files, no previous state) |
| 1 | no plan or model (`run sherpa plan first`), stale plan, both homes and no terminal to ask |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| An agent shows `no unit matches` although it is about one module | it names neither the unit's slug nor its repository path twice | mention the module path (`src/Shop.Pricing`) in the agent, or rename the file to the slug; re-run `adopt` |
| `ambiguous: A and B mentioned 3× each` | two units are mentioned equally often | make the file about one unit, or accept the entry in the plan and keep your file as it is |
| A generated file shows `block facts differs … — stays` after a rebuild | the file was written by an older model or hand-edited; adopt cannot tell the two apart | if it was an old rendering, remove the block's lines between the markers and run `apply` — a missing block is skipped, not re-added; or delete the file and let `apply` recreate it |
| `a .agents/skills/x/SKILL.md … covers the entry` but you want sherpa's skill | your file sits at sherpa's path | rename yours or set `decision: accept` on the entry |
| Nothing listed for `.claude/memory/` or `settings.local.json` | git-ignored files are not the harness | nothing — that is the intent |

## See also

[`sherpa apply`](apply.md) · [`sherpa status`](status.md) · [`sherpa plan`](plan.md) (`covered`) ·
[concepts/harness-apply.md](../concepts/harness-apply.md#adopt--existing-harnesses-and-a-rebuildable-state) ·
ADR-0007, ADR-0016, ADR-0017.
