---
name: e2e-test
description: "End-to-end test of the sherpa CLI on one local corpus repository: every claim in README, CLAUDE.md and the ADR index is a thesis in tests/e2e (one pytest per claim, the sherpa command as a subprocess, the proving line recorded); the lifecycle doctor → scan → plan → apply → status/check → adopt → apply --remove runs against a real repository and the corpus is left exactly as found. Use for 'e2e test', 'does the README hold', 'test the lifecycle on the corpus', before a release, after a milestone slice. Optional argument: the corpus path (default $SHERPA_E2E_REPO) and a focus (a thesis id)."
---

# e2e-test — the theses of README, CLAUDE.md and the ADRs, measured on a real repository

The theses live in code: `tests/e2e/test_theses.py`, one test per claim, the claim and its source in the
`thesis` marker, the output line that proves it recorded with `ev` and printed as a table at the end
(ADR-0055). CI runs the same suite on the built-in corpus; this skill runs it on the corpus repository —
the run every release is measured by.

## Run

```bash
export SHERPA_NO_UPDATE_CHECK=1
R="${1:-$SHERPA_E2E_REPO}"                       # the corpus repository: an argument, else the ignored local setting
git -C "$R" status --short --ignored | grep -q . && { echo "corpus not clean — stop, ask"; exit 1; }
SHERPA_E2E_REPO="$R" .venv/bin/pytest tests/e2e -q 2>&1 | tee /tmp/e2e-run.txt | tail -60
```

The suite does the rest: verifies the corpus clean including ignored files, fetches once (every `scan` and
`plan` runs with `--no-fetch`), runs the theses in lifecycle order, takes the harness back, scrubs what a
thesis left and verifies the corpus clean again — also after a failure. A focus (`-k T11`) runs the phases a
thesis needs and nothing else; a full run is the release check.

Read the table under `e2e theses — corpus: external`: `PASS` with its evidence, `FAIL` with the assertion
above it, `BLOCKED` where an earlier phase failed (the failing line is the reason), `SKIP` for a platform
thesis. The corpus path reads `<corpus>` there; unit names in the evidence are the corpus's — they stay in
the chat.

## Report — this shape, every time

1. **verdict** — three sentences: release-ready or not; the most expensive break; what holds.
2. **theses** — the table as printed, `id · result · claim · source · evidence`.
3. **findings** — per FAIL: what a user sees, the smallest reproduction in neutral terms ("the root unit",
   "a nested unit three levels deep"), which ADR it touches (or contradicts), the programmatic fixture that
   would catch it in `tests/` (shape, not code). A thesis whose source sentence is ambiguous goes to `open`,
   not into FAIL.
4. **cleanup** — the empty `git -C "$R" status --short --ignored` line and `ls -a "$R" | grep -E '^\.(sherpa|agents|claude)$'` printing nothing.
5. **open** — questions for Andrei with a recommendation each.

Every FAIL and every side-finding names the programmatic fixture that will catch it in `tests/` from then on;
the fix that follows (`milestone-step`) lands that fixture with the change — an e2e finding without a fixture
is not closed. The list of past findings is plan §13 (F49 onwards).

## A new claim, a changed command

A new sentence in README, CLAUDE.md or an ADR that a user will rely on is a new test in
`tests/e2e/test_theses.py` with a `thesis` marker (id, claim, source) and an `ev` line — in lifecycle order,
asking for the phase it needs (`planned`, `installed`, `uninstalled`, or `clean_slate` for a thesis that
starts from the uninstalled corpus). A command whose output changes turns its thesis red in CI: change the
thesis with the command, in the same pull request. Numbers stay relative so the built-in corpus and a real
one pass the same assertion.

## Don't

- Name the corpus, its units or its authors in anything that could be committed; numbers in the report are
  fine in the chat, never in a file of this repository.
- Run a subset and call it a release check — a thesis skipped because it "obviously holds" is how the root
  unit's link (F49) was missed.
- Fix what you find: report, then `milestone-step`. The suite writes only into the corpus and takes it back.
- Run `git fetch` in the corpus between two theses, or the suite against the Sherpa clone itself.
