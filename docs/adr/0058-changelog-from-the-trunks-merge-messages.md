# ADR-0058 — The changelog is laid out from the trunk's merge messages, never written by hand

**Status:** accepted · **Date:** 2026-09-21 · **Deciders:** Andrei · **Relates to:** ADR-0018 (releases per
tag), ADR-0009 (`main` only through squash-merged pull requests), CLAUDE.md (commit messages are one to three
full sentences; every fact has one owner)

## Context

M2c's last open item before the announcement was "a `CHANGELOG.md` generated from the release notes".
`release.yml` creates the GitHub release with `--generate-notes` — GitHub's list of pull request titles — and
the repository had no changelog file. Two sources for "what changed" would violate the owner principle; a
hand-written changelog is the file every project forgets to update (Keep a Changelog's own guidance is to
write it as you go, which is what a squash-merge message already is here: every merge into `main` is one commit
whose message says what changed and why, in sentences, with the pull request number).

## Decision

1. **`scripts/changelog.py` renders `CHANGELOG.md`** from `git tag -l 'v*'` and `git log --no-merges` of the
   trunk: one section per tag, newest first, headed `## v<version> — <date>` (the tag's date; tags are
   lightweight, so it is the commit's), one bullet per merge below it — the commit's subject, the trailing
   `(#NN)` turned into a link to the pull request. Commits after the newest tag are `## Unreleased`.
2. **The bump pull request renders the coming release's section.** When `__version__` in
   `src/sherpa/__init__.py` is newer than the newest tag, the commits since that tag are headed
   `## v<__version__> — <date of HEAD>` instead of `Unreleased`; the tag lands on that commit, so a re-render
   after the tag is byte-identical. `release.yml` refuses a tag whose section is missing — the same guard it
   has for the version.
3. **Nothing in the file is edited by hand.** The sentence a reader should see lives in the merge message, once;
   a wrong entry is a wrong commit message, fixed the next time the file is rendered from a corrected history —
   in practice never, which is the point: what was merged is what happened.
4. `--check` says whether the checked-in file is what git says; the test suite checks that every release
   section the history has is in the file (on a clone with tags — CI's shallow checkout has none, the release
   workflow's guard covers that side).

## Reasoning

- Stdlib, deterministic, one input (the history), no service — the same rules as `render-demo.py`.
- GitHub's generated notes stay on the release page as they are; the file in the repository is the durable,
  greppable form and reads the same offline and on PyPI's project page.
- "Unreleased" between releases is honest: a merge that is not on PyPI yet is not in a release section.

## Consequences

- `CHANGELOG.md` at the root, 14 releases from `v0.5.0` to `v0.8.4` on the day of the decision, linked from
  the README's roadmap line; `docs/plan.md` M2c row closes the item.
- The milestone ritual's release step runs the script in the bump pull request; `release.yml` guards it.
- `tests/test_changelog.py`: the layout on a programmatic trunk, the bump case, the tag-on-tag case, `--check`,
  and the checked-in file against the history.
