# `sherpa check`

Structural rules for a harness under `.claude/`: front matter Claude Code needs, manifest paths that resolve,
file links that resolve, intact block markers, hook wiring, size budgets, drift against the state. Deterministic,
seconds, no LLM — and it runs without sherpa installed, because `apply` deploys the same file into the repo.

## Synopsis

```
sherpa check [REPO] [--json] [--strict]
python3 .agents/scripts/sherpa-check.py [REPO] [--json] [--strict]      # the deployed copy (<home>/scripts/)
```

## Scope

With a state (`.sherpa/state.json`), C1 to C5 are FAIL only in the files sherpa generated (`origin: generated`).
In every other file under the homes — adopted or unrecorded, yours either way — they are WARN with the suffix
`(yours)`: a vendored
skill with a dead link or a refinement note that points at a moved file is worth a line, not a red exit
(ADR-0047). `--strict` makes them FAIL everywhere; without a state nothing is managed yet and every rule is
strict. C6 (hook wiring), C7 (budgets) and C8 (drift) do not change. `apply` checks with the files it is about
to write counted as managed and rolls back only on a **new** FAIL (ADR-0032); `status` shows the same counts.

## Rules

| Rule | Level | Checks | Typical message |
|---|---|---|---|
| C1 | FAIL | every `.claude/agents/*.md` has front matter with `name` and `description` — Claude Code ignores an agent without them | `front matter has no description` |
| C2 | FAIL | every `SKILL.md` under `.claude/skills/` or `.agents/skills/` has front matter with `name` and `description` | `no front matter (name, description required)` |
| C3 | FAIL | every path under `knowledge.always` and `knowledge.on_demand` in an agent's front matter exists, relative to `.claude/` | `knowledge path docs/modules/pay.md does not exist` |
| C4 | FAIL | relative **file** links (`[x](../docs/modules/pay.md)`) in `.claude/**`, `.agents/**` and every `CLAUDE.md`/`AGENTS.md` (root and nested) resolve. Skipped: URLs, `mailto:`, anchors, absolute paths, targets without a file extension (wiki pages), and anything under `archive/` (history may tell the old state). A harness file that is a symlink pointing nowhere is a C4 too (sherpa writes no symlinks, so with a state it is always yours — a WARN) | `link target ../nope.md does not exist` · `symlink target nowhere.md does not exist` |
| C5 | FAIL | `sherpa:begin <name>` / `sherpa:end <name>` markers are balanced, correctly nested (none) and unique per file | `managed block markers: line 12: end facts without matching begin` |
| C6 | FAIL | `.claude/settings.json` parses as JSON; every hook command that references `$CLAUDE_PROJECT_DIR/<path>` points to an existing file | `Stop hook references missing file .claude/hooks/sherpa-outcome.py` |
| C7 | WARN | size budgets: agent > 150 lines, owner doc > 600, skill > 250 — a fat agent is a rotation candidate (facts belong in the owner doc); a nested `CLAUDE.md`/`AGENTS.md` > 8 KiB, the root one > 32 KiB — runtimes inject them whole (ADR-0029) | `162 lines > budget 150 (agent)`, `9886 bytes > budget 8 KiB (nested proximity file)` |
| C8 | WARN | with `.sherpa/state.json`: managed files or blocks whose hash differs from the state, blocks removed, files missing | `block facts hand-edited` |

Findings are sorted FAIL first, then by rule and path. Exit 1 when at least one FAIL.

## Options

| Option | Effect |
|---|---|
| `REPO` | repository root (default `.`; the deployed copy also honours `$CLAUDE_PROJECT_DIR`) |
| `--json` | findings as a JSON array of `{level, rule, path, message}` — for CI annotations and editors |

## Output

```console
$ sherpa check .
sherpa check /path/shop: 2 FAIL, 1 WARN
  FAIL C3 .claude/agents/pay.md: knowledge path docs/modules/pay.md does not exist
  FAIL C5 CLAUDE.md: managed block markers: block harness is never closed
  WARN C7 .claude/agents/pay.md: 162 lines > budget 150 (agent)
```

## The deployed copy

`sherpa apply` writes `src/sherpa/check.py` — one stdlib-only file — as `<home>/scripts/sherpa-check.py` with
the sherpa version stamped in, and records it as a managed file. Run directly, it:

1. tries `import sherpa.check` and, when an installed sherpa is found, delegates to it — installed rules are never
   older than the copy;
2. otherwise applies its own rules, identical to the version that deployed it.

`SHERPA_CHECK_STANDALONE=1` forces the copy to run its own rules (useful to verify what colleagues without sherpa
see). `sherpa status` notes when the copy is older than the installed sherpa; the next `apply` refreshes it.
There is exactly one implementation of the rules (ADR-0013).

## Exit codes

| Exit | When |
|---|---|
| 0 | no FAIL (warnings allowed — including `(yours)` findings) |
| 1 | at least one FAIL: in a managed file, or anywhere with `--strict` or without a state |

## Use in CI

```yaml
- run: python3 .agents/scripts/sherpa-check.py      # no sherpa install needed (.claude/scripts/ when home is .claude)
```

or, with sherpa installed, `sherpa check`. Pair it with `sherpa status` when you also want drift in the log.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Dozens of C4 FAILs on an existing harness before the first `apply` | genuinely broken relative links (moved files); without a state every file is strict | run `apply` or `adopt` once — the state scopes them to WARN `(yours)`; fix the ones you care about; `--strict` lists them all as FAIL again |
| `WARN C4 … (yours)` | a dead link in a file sherpa did not generate — adopted or not | fix it or leave it; the exit code is not affected |
| C4 on a link that exists | the link is relative to the *file's directory*, as markdown resolves it — not to the repo root | rewrite the link |
| C1 on an agent that works | the front matter has `name:` but no `description:` — Claude Code still lists it, but routing needs the description | add one |
| C6 after moving the repo | absolute paths in hook commands | use `$CLAUDE_PROJECT_DIR`, as sherpa does |
| C5 inside YAML front matter | a `# sherpa:begin …` line was edited | restore the pair; `apply` never touches the rest of the front matter |

## See also

[`sherpa apply`](apply.md) (rollback on new FAILs) · [`sherpa status`](status.md) ·
[concepts/harness-apply.md](../concepts/harness-apply.md#checker-rules--sherpa-check-and-the-deployed-copy) ·
ADR-0013.
