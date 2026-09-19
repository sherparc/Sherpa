---
name: e2e-test
description: "End-to-end test of the sherpa CLI on one local corpus repository: every claim in README, CLAUDE.md and the ADR index becomes a thesis with a command and a pass criterion; the whole lifecycle doctor → scan → plan → apply → status/check → adopt → apply --remove runs against a real repository and the corpus is left exactly as found. Use for 'e2e test', 'does the README hold', 'test the lifecycle on the corpus', before a release, after a milestone slice. Optional argument: the corpus path (default $SHERPA_E2E_REPO) and a focus (a thesis id, a command)."
---

# e2e-test — the theses of README, CLAUDE.md and the ADRs, measured on a real repository

## Setup — the same every run

```bash
S="$PWD/.venv/bin/sherpa"                      # run from the Sherpa clone; the tester never installs
R="${1:-$SHERPA_E2E_REPO}"                     # the corpus repository: an argument, else the ignored local setting
export SHERPA_NO_UPDATE_CHECK=1                # no release check, no daily hint in any output
test -d "$R/.git" || { echo "no corpus at $R"; exit 1; }
git -C "$R" status --short --ignored | grep -q . && { echo "corpus not clean — stop, ask"; exit 1; }
git -C "$R" fetch origin -q                    # once; every scan/plan below runs with --no-fetch
```

`$R` is never named in the report as a path fragment that identifies it — write "the corpus" and refer to
units by role ("the root unit", "the most active unit"), not by name.

## The thesis catalogue — run all, in this order

Each thesis: the claim, its source, the command(s), the pass criterion. Record the exit code (`echo $?`,
`${PIPESTATUS[0]}` behind a pipe) and the one output line that proves it. `[esc]` marks the escape to use
when an earlier failure blocks the thesis; say in the report when one was used.

| id | claim | source |
|---|---|---|
| T01 | `doctor` reports every prerequisite with a fix and ends `ready`; exit 0 | README quick start, ADR-0018 |
| T02 | `scan` is deterministic: same trunk rev → byte-identical model; sorted, no clock | README § Determinism, ADR-0003 |
| T03 | `scan` measures `origin/<trunk>`, never `HEAD`: a detached checkout gives the same model | ADR-0003 |
| T04 | `scan` speed: files and wall time (`… modules in N.N s →`) in the summary line; compare with the README's benchmark | README § scanner |
| T05 | `plan`: proposals and reasoned no's; every entry carries `✓`/`✗` checks; dormant and out-of-reach units are listed, never dropped | README § planner, ADR-0006/0012/0014 |
| T06 | `plan` twice → byte-identical YAML; `--accept`/`--reject` survive a re-plan | ADR-0012 |
| T07 | `apply` is dry run first: without `--yes` and without a terminal nothing is written; `--dry-run` never writes | ADR-0008 |
| T08 | `apply --yes` writes the listed files, runs the checker, records `harness_rev`; exit 0; `check: 0 FAIL` | README, ADR-0013 |
| T09 | a rollback is complete — write error or new checker FAIL, both share `_roll_back`: exit 1, `git status --short --ignored` empty, **no empty `.agents/`/`.claude/` left**, the next `apply` not blocked. From outside only the write-error path can be provoked (a read-only unit directory); the checker path is the programmatic fixture `test_rollback_takes_the_directories_it_created_with_it` | ADR-0013/0032 |
| T10 | idempotent: the second `apply --dry-run` says `nothing to do.`; `status` says `drift: none` | README, ADR-0013 |
| T11 | never overwrite: prose outside the markers survives a re-apply; a hand edit inside a block is yours — reported, not rewritten | ADR-0016/0030 |
| T12 | facts stamp carries the window end, not today's date | ADR-0019 |
| T13 | proximity budgets: every nested `AGENTS.md`/`CLAUDE.md` ≤ 8 KiB, root ≤ 32 KiB | ADR-0029 |
| T14 | links resolve: `check` C4 clean in every file sherpa wrote — including the root unit's | ADR-0047 |
| T15 | `adopt` rebuilds a lost state with the same `harness_rev` `apply` wrote | README, ADR-0017 |
| T16 | `adopt` never changes a byte of a hand-written harness file; lists it as `a`/`?` | ADR-0007 |
| T17 | a nested `AGENTS.md` at a unit's path covers its owner-doc entry; `apply` appends the facts block and creates no skeleton | ADR-0049 |
| T18 | one repository: a nested `.git` stops `apply`/`adopt` with the way out named; `doctor` says it first; dry runs go on with a note | ADR-0045 |
| T19 | both homes present and nothing decides: dry runs assume `.agents` and say so; a write without a terminal refuses with the fix named. Set up on the clean corpus with two empty home directories — on an installed harness the checker copy decides the home (ADR-0036 §3) and nothing is asked; this is also the F50 regression check | ADR-0036 |
| T20 | `--json` on `status`, `check`, `doctor` parses; exit codes are 0/1 only; errors on stderr as `sherpa <cmd>: <msg>` naming the fix | files-and-exit-codes.md |
| T21 | `apply --remove` uninstalls: `git status --short --ignored` as before the first apply; a hand-edited file stays | ADR-0048 |
| T22 | README numbers are true: test count and coverage of `pytest -q --cov=sherpa` match the README | CLAUDE.md § README |

### Commands per thesis

```bash
# T01
$S doctor --offline "$R"; echo "exit=$?"                       # every line ✓, last line "ready — …"
# T02 · T04
$S scan "$R" --no-fetch; cp "$R/.sherpa/codebase-model.json" /tmp/e2e-m1.json
$S scan "$R" --no-fetch; cmp "$R/.sherpa/codebase-model.json" /tmp/e2e-m1.json && echo T02 identical
python3 -c "import json;g=json.load(open('$R/.sherpa/codebase-model.json'))['git'];print(g['windows']['as_of'],g['trunk'])"
# T03 — detached HEAD, then back; the model must not change
B=$(git -C "$R" rev-parse --abbrev-ref HEAD); git -C "$R" checkout -q HEAD~3
$S scan "$R" --no-fetch; cmp "$R/.sherpa/codebase-model.json" /tmp/e2e-m1.json && echo T03 identical
git -C "$R" checkout -q "$B"
# T05 · T06
$S plan "$R" --no-fetch | tee /tmp/e2e-plan1.txt | tail -4      # proposals, no's, dormant, out of reach
cp "$R/.sherpa/harness-plan.yaml" /tmp/e2e-p1.yaml
$S plan "$R" --no-fetch >/dev/null; cmp "$R/.sherpa/harness-plan.yaml" /tmp/e2e-p1.yaml && echo T06 identical
grep -c "✓" /tmp/e2e-plan1.txt; grep -cE "^  - " /tmp/e2e-plan1.txt   # checks present, no's present
$S plan "$R" --no-fetch --reject "agent:$(grep -m1 '^  + agent' /tmp/e2e-plan1.txt | awk '{print $3}')" | tail -1   # (1 decided now)
$S plan "$R" --no-fetch | tail -1                                  # → … (1 decisions kept): the decision survived the re-plan
# T07
$S apply "$R" </dev/null | tail -1; echo "exit=${PIPESTATUS[0]}"  # "dry run only — pass --yes …", exit 0
$S apply --dry-run "$R" | tail -1; git -C "$R" status --short --ignored   # only "?? .sherpa/"
# T08
$S apply --yes "$R" | tail -3; echo "exit=${PIPESTATUS[0]}"
git -C "$R" status --short --ignored | head -3
find "$R" -maxdepth 1 \( -name .agents -o -name .claude \) -type d   # after a rollback: must print nothing
#   [esc] on a rollback: rm -rf "$R/.agents" "$R/.claude"; $S apply --yes --no-check "$R" — and say so
# T09 — after T21 on the clean corpus: a fresh install that fails half-way (a read-only nested unit directory)
#   chmod a-w "$R/<a nested unit's directory>"; $S apply --yes "$R" | tail -2; echo "exit=${PIPESTATUS[0]}"   # write failed … rolled back
#   git -C "$R" status --short --ignored; find "$R" -maxdepth 1 \( -name .agents -o -name .claude \) -type d   # only ?? .sherpa/, no dirs
#   chmod u+w "$R/<that directory>"; $S apply --dry-run "$R" | sed -n 1p                                      # home: .agents — no question
# T10
$S apply --dry-run "$R" | tail -1                                  # nothing to do.
$S status "$R" | sed -n 1,4p                                       # drift: none — files match …
# T11 — outside the markers, then inside
P=$(.venv/bin/python -c "import yaml;p=yaml.safe_load(open('$R/.sherpa/harness-plan.yaml'));print(next(e['scope'] for e in p['entries'] if e['kind']=='owner-doc' and e['default']=='propose' and e['scope']))")
F="$R/$P/AGENTS.md"; cp "$F" /tmp/e2e-f.bak                       # the most active nested unit's proximity file
printf '\nTeam note — keep me.\n' >> "$F"; $S apply --dry-run "$R" | tail -1   # nothing to do.
sed -i 's/^| dependents |/| dependents (edited) |/' "$F"; $S status "$R" | grep -E "hand-edited" | head -3   # ! … block facts hand-edited (skipped)
cp /tmp/e2e-f.bak "$F"                                             # sherpa's bytes again, so T15 compares like with like
# T12
grep -rho "as of [0-9-]*" "$R/.agents/docs/modules" | sort -u; date -I   # the stamp = as_of, not today
# T13
find "$R" -name AGENTS.md -o -name CLAUDE.md | xargs wc -c | sort -n | tail -3   # nested ≤ 8192, root ≤ 32768
# T14
$S check "$R"; echo "exit=$?"                                      # 0 FAIL — including the root AGENTS.md
# T15 — a lost state
REV=$(python3 -c "import json;print(json.load(open('$R/.sherpa/state.json'))['harness_rev'])")
rm "$R/.sherpa/state.json"
$S adopt "$R" | tail -1                                            # T15: … rebuilt … harness_rev <same>
# T19 — after T21 on the clean corpus: two empty homes, nothing decides
#   mkdir "$R/.agents" "$R/.claude"; $S plan "$R" --no-fetch >/dev/null
#   $S apply --dry-run "$R" 2>&1 | grep note                        # note: both .agents/ and .claude/ exist … assumes .agents
#   $S apply --yes "$R" </dev/null 2>&1 | head -1; echo "exit=${PIPESTATUS[0]}"   # sherpa apply: both … exist — … exit 1
#   rmdir "$R/.agents" "$R/.claude"

python3 -c "import json;print(json.load(open('$R/.sherpa/state.json'))['harness_rev'])"; echo "was $REV"
# T16
mkdir -p "$R/.claude/agents"; printf -- '---\nname: ops\ndescription: mine\n---\n# ops\n' > "$R/.claude/agents/ops.md"
sha256sum "$R/.claude/agents/ops.md"; $S adopt "$R" | grep -E "ops.md"; sha256sum "$R/.claude/agents/ops.md"
rm "$R/.claude/agents/ops.md"
# T17 — after T21 has uninstalled: an own AGENTS.md at a unit's path, then plan + dry run
# T18 — a nested repository, temporarily
git -C "$R" init -q nested-tmp; $S doctor --offline "$R" | grep -i repositor; $S apply --dry-run "$R" | sed -n 1,3p
$S adopt "$R"; echo "exit=$?"; rm -rf "$R/nested-tmp"             # exit 1, the way out named
# T20
for c in status check doctor; do $S $c --json "$R" | python3 -m json.tool >/dev/null && echo "$c json ok"; done
$S apply --yes /tmp 2>&1 | head -1; echo "exit=${PIPESTATUS[0]}"    # sherpa apply: … exit 1
# T21
$S apply --remove --yes "$R" | tail -2; git -C "$R" status --short --ignored   # empty, or only the hand-edited file
# T22 — in the Sherpa clone
.venv/bin/pytest -q --cov=sherpa 2>&1 | tail -3; grep -n "tests, ~" README.md
```

T17 runs after T21 on the clean corpus: `printf '# Notes\n\nOurs.\n' > "$R/<unit path>/AGENTS.md"`, then
`plan` must show `[covered by <unit path>/AGENTS.md]` on that owner-doc entry and `apply --dry-run` must list
that file as `~` (block appended) and no `<home>/docs/modules/<unit>.md` for it. Remove the file afterwards.

## Cleanup — non-negotiable, also after an aborted run

```bash
$S apply --remove --yes "$R" >/dev/null 2>&1 || true
rm -rf "$R/.sherpa" "$R/.agents" "$R/.claude" "$R/nested-tmp"
git -C "$R" checkout -q -- . ; git -C "$R" clean -qfd -- ':!.idea'   # only sherpa's leftovers can be here
git -C "$R" status --short --ignored                                  # must print nothing
rm -f /tmp/e2e-*
```

A corpus that was dirty before the run is never cleaned with `git clean` — stop at the preflight and ask.

## Report — this shape, every time

1. **verdict** — three sentences: release-ready or not; the most expensive break; what holds.
2. **theses** — table `id · claim · result (PASS / FAIL / BLOCKED / PASS-behind-escape) · evidence` (the
   exit code and the output line, in neutral terms: "the root unit", "a nested unit three levels deep").
3. **findings** — per FAIL: what a user sees, the smallest reproduction in neutral terms, which ADR it
   touches (or contradicts), the programmatic fixture that would catch it in `tests/` (shape, not code).
4. **cleanup** — the empty `git status --short --ignored` and the empty `find … -type d` line.
5. **open** — questions for Andrei with a recommendation each; a thesis whose source sentence is ambiguous
   goes here, not into FAIL.

Every FAIL and every side-finding names the programmatic fixture that will catch it in `tests/` from then on
(shape: the repository it needs, the command, the assertion). The fix that follows (`milestone-step`) lands
that fixture with the change — an e2e finding without a fixture is not closed, and the fixture list of this
skill's past findings is plan §13 (F49 onwards).

## Don't

- Name the corpus, its units or its authors in anything that could be committed; numbers in the report are
  fine in the chat, never in a file of this repository.
- Skip a thesis because it "obviously holds" — the root unit's link (T14) looked obvious too.
- Fix what you find: report, then `milestone-step`. The only files this skill writes live in the corpus
  and in `/tmp`, and all of them are gone at the end.
- Run `git fetch` between two theses, or `apply --yes` on the Sherpa clone itself.
