# ADR-0052 — The contribution path: DCO sign-off checked by CI, Contributor Covenant, a security policy

**Status:** accepted · **Date:** 2026-09-19 · **Decision:** Andrei (launch slice M2c) ·
**Takes:** ADR-0010 §4 (CLA or DCO from the first external pull request) · **Code:** `CONTRIBUTING.md`,
`CODE_OF_CONDUCT.md`, `SECURITY.md`, `.github/workflows/dco.yml`, `.github/ISSUE_TEMPLATE/`,
`.github/pull_request_template.md`

## Context
With the licence public (ADR-0051) the repository can take a pull request from outside, and ADR-0010 §4 said it
must not before the right to relicense is preserved. GitHub's community profile lists the files a reader expects
on a public repository — contributing guide, code of conduct, security policy, templates — and their absence is
the first thing a contributor notices. Three choices had to be made: CLA or DCO, which code of conduct, and how
the sign-off is enforced.

## Decision
1. **DCO, not a CLA.** A `Signed-off-by:` line on every commit (`git commit -s`; `git config format.signoff true`
   once per clone) is the contributor's statement under the
   [Developer Certificate of Origin](https://developercertificate.org/) that they may contribute the change under
   the repository's licence. No document to sign, no registry of signers; the sign-off travels with the commit.
   It applies to the maintainer's commits as well — one rule for every pull request.
2. **Enforced by an own workflow**, `dco.yml`: on every pull request it reads the pull request's commits through
   the GitHub API with the job's own token and fails when a non-merge commit lacks the line. Its own workflow,
   not a job in `ci.yml`, because `ci.yml` skips docs-only changes (ADR-0043) and the sign-off rule has no such
   exception. No third-party app: the check is fifteen lines of shell and `jq`, readable in the repository.
3. **Contributor Covenant 2.1, verbatim**, with the maintainer's address as the contact. It is the text most
   contributors have already read; a house text would be read as a statement.
4. **A security policy that names the surface**: `apply` writing outside its markers, a path escaping the
   repository, the hook or the checker executing anything but what they ship, `self-update` installing something
   else. Private reporting through GitHub's advisory form or by email, an answer within seven days, a patch
   release with an advisory. Supported: the latest tag only.
5. **Templates ask for what a report needs**: `sherpa doctor --json` and the command for a bug, the evidence
   for a feature — Sherpa proposes only what it can reason about, so the reason is the feature — and the pull
   request template lists the five things the reviewer checks.

## Alternatives
- **CLA** (Apache-style, a signing bot): rejected — a CLA is a contract each contributor has to read and a
  registry the maintainer has to keep; the DCO gives the same relicensing right for the case that matters (the
  commit is the contributor's own work, offered under the licence) and is what the Linux kernel, GitLab and
  Docker use.
- **The DCO GitHub App**: rejected — a third-party app with write access to checks, for a check that fits in
  one shell step (ADR-0001's stdlib-first, applied to the repository).
- **Exempting the maintainer's commits from the sign-off**: rejected — the check would need a list of names,
  and the maintainer's own history would be the one without the statement.

## Consequences
- The commit rule in `CLAUDE.md` gains the sign-off: one to three sentences, `Signed-off-by:` as the only
  trailer, never `Co-Authored-By`.
- `README.md` links `CONTRIBUTING.md` and `SECURITY.md` from `## Development`; the once-per-clone block gains
  `git config format.signoff true`.
- GitHub's private vulnerability reporting has to be enabled once in the repository's settings (a click by the
  owner, not a file); until then the email in `SECURITY.md` is the way.
- Squash merges keep the sign-off lines of the squashed commits in the merge commit's body — GitHub's default;
  nothing to configure.
