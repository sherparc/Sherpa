# ADR-0056 — `harness_rev` over what an agent reads; the tooling and the sherpa version hashed apart

**Status:** accepted · **Date:** 2026-09-20 · **Deciders:** Andrei · **Amends:** ADR-0008 (the outcome minimum:
what the label is stamped with), ADR-0028 (the denominator: what a revision is), ADR-0029 (the proximity budget
is sherpa's for files it seeded, the ceiling for the team's), ADR-0042 (the state is validated on every read),
ADR-0047 (a file git ignores is outside the checker's scope, like `adopt`'s)

## Context

`harness_rev` was the hash over every state record plus the sherpa version (`state.py`). Every `self-update`
followed by `apply` — the checker copy and the hook carry the version, and the version itself was hashed —
started a new revision although no owner doc, agent, skill or proximity block had changed. Measured on the
repository that has run the outcome hook longest (plan §14 F58): 178 labelled executions spread over 22
revisions in three days, the busiest revision at n = 21 — below the 30 ADR-0028 requires before two revisions
are compared. M5 would have shipped with no comparable sample anywhere, and the first labels collected on a
corpus repository would restart on the next tag. Terraform keeps `terraform_version` in the state apart from
the identity of the resources for the same reason.

Three smaller things were found in the same review and are decided here because they touch the same files:
the C7 budget of 8 KiB (ADR-0029, Hermes' *recommendation*) fired on eight nested `AGENTS.md` written by the
maintainers of that very runtime, before sherpa had written a byte (F59); the checker walked git-ignored
directories that `adopt` already treats as not the harness (F62); the state was validated in the tests but not
on read, so a hand-merged `state.json` with a record no sherpa wrote reached `apply` (F66); and `settings.json`
with a `hooks` key in somebody else's shape crashed the preview with a traceback (F60).

## Decision

1. **`harness_rev` is the hash over the content records only** — every record whose path ends in `.md`: owner
   docs, agents, skills, root and nested proximity files, adopted ones included. It changes exactly when
   something an agent reads changes, never with the sherpa version.
2. **`tooling` is the second hash**, over the remaining records — the checker copy, the hook, the hook entries
   in `settings.json`, the ignore file — plus the sherpa version. It is written to the state next to
   `harness_rev` and moves with every upgrade; the outcome label already carries `sherpa: <version>`, so the
   hook is unchanged and M5 can group by either.
3. **The state is validated against the shipped schema on every read** (`state.load`), as ADR-0042 already does
   for the plan; a foreign record is refused with its location and `sherpa adopt` as the way out. The schema
   tolerates unknown top-level keys, so an older sherpa reads a newer state (the model keeps trusting its writer —
   it is 5 MB on a large repository and never edited by hand).
4. **C7's 8 KiB budget applies to proximity files sherpa seeded** — a managed file, or a blocks file that still
   carries its whole-file hash (ADR-0048). A `CLAUDE.md`/`AGENTS.md` the team wrote, with or without sherpa's
   appended block, gets one line only above the 32 KiB ceiling where the runtime truncates it, marked `yours`.
   Without a state, and with `--strict`, the budget applies everywhere as before.
5. **A file git ignores is not checked.** `check` asks `git check-ignore` for the harness files it found; a
   tracked file is never ignored, and outside a repository or without git the directory list decides as
   before. The deployed copy does the same — `subprocess` is stdlib, the file stays one.
6. **`settings.json` in somebody's shape is skipped, never rewritten and never a traceback**: a `hooks` key that
   is not an object of event lists yields `! hooks is not an object of event lists — yours (skipped)`, the
   same guard the removal side already had.

## Reasoning

- The product's central claim is measured per `harness_rev` (§2.5, §9); a revision that moves with the tool
  compares tool releases, not harnesses. Content is what the runtime injects — markdown; the rest is plumbing.
  The split by suffix is deliberate: it needs no field on the record, a rebuilt state (`adopt`) computes the same
  two values, and the empty harness has one revision for every version from here on.
- The 8 KiB figure was a recommendation read in Hermes' source (§10 F9); its own repository has eight nested
  files above it and none above the ceiling. A warning the runtime's authors would ignore trains the team to
  ignore C7. The ceiling is the fact; the budget is sherpa's discipline for the files it is responsible for.
- Two rules for "what is the harness" — `adopt` drops ignored files, `check` walked them — put a permanent WARN
  on an ignored vault in the repository and would find every `AGENTS.md` inside a vendored package. One rule,
  git's.
- Validating on read costs a few milliseconds on a file of a few hundred records and closes the one path by
  which a record no writer produced reached the write path (a conflict resolved by hand, §11 F30).

## Consequences

- The state gains an optional `tooling` key (schema version stays 1; a state written before this ADR reads
  with `tooling: ""` and `apply` fills it on the next write). Every existing harness gets a new `harness_rev`
  once — the last time a release moves it.
- Goldens that print a `harness_rev` no longer change with the version; the empty harness is
  `e3b0c44298fc` everywhere.
- `status` shows the current revision, then the five most recent by their first label, and counts the rest
  (§14 F65); `--json` carries all.
- `apply` and `check` on the corpus repository with twelve hand-written nested `AGENTS.md` report 0 WARN
  where 8 (9 after `apply`) stood.
- Theses E10 (the revision survives a changed checker copy), E11 (the ceiling for the team's files) and E12
  (ignored files are not checked) in `tests/e2e`.
