# ADR-0053 — PyPI is the index: trusted publishing on every tag, `self-update` reads it first

**Status:** accepted · **Date:** 2026-09-19 · **Decision:** Andrei (launch slice M2c) · **Takes:** ADR-0018 §5 ·
**Amended by:** ADR-0054 (the project is `sherparc`, not `sherpa-harness`) ·
**Code:** `.github/workflows/release.yml`, `src/sherpa/update.py`, `src/sherpa/doctor.py`

## Context
ADR-0018 chose GitHub Releases as the index because the repository was private and set the condition: "PyPI at
the public release — `release.yml` gains a publish step and `self-update` switches to the index". ADR-0051 made
the release public. Until now a user installed with `uv tool install git+https://…`, `self-update` needed a
GitHub token for the wheel or git credentials for the tag, and `doctor` on a machine without either warned
`no access without a token`. The name `sherpa-harness` (ADR-0009) is free on PyPI (checked 2026-09-19).

## Decision
1. **`release.yml` publishes the wheel and the sdist to PyPI on every tag, after the GitHub release**, through
   trusted publishing (`pypa/gh-action-pypi-publish`, OIDC, `permissions: id-token: write`, environment `pypi`):
   no API token in the repository or its secrets. The order matters — a publisher not yet registered on pypi.org
   fails the last step and leaves a usable GitHub release behind. The job refuses a tag whose version the index
   already has, before building: a version is published once (PyPI would refuse it too, after the tests ran).
2. **`self-update` and `doctor` read PyPI first, without a token**: `GET https://pypi.org/pypi/sherpa-harness/json`,
   the version under `info.version`. The installer fetches the wheel itself — the source is the pinned requirement
   `sherpa-harness==<version>` for `uv tool install`, `pipx install` and `pip install` alike; sherpa downloads
   nothing.
3. **GitHub stays the fallback, unchanged** (ADR-0018, ADR-0035): when the index has no project yet or cannot be
   reached, the Releases API with a token, else the newest tag by `git ls-remote`. `Release.index` names which
   one answered; `doctor` prints it (`current (via PyPI)`).
4. **The README's install line is `uv tool install sherpa-harness`**; the git URL stays as the way to run `main`
   or to pin a tag without the index.

## Alternatives
- **An API token in the repository secrets**: rejected — a long-lived credential where OIDC gives a short-lived
  one per run, and PyPI's own recommendation is trusted publishing.
- **PyPI only, GitHub fallback removed**: rejected — a machine behind a proxy that allows github.com and not
  pypi.org exists in the customer world, and the fallback costs one function that already has its tests.
- **GitHub first, PyPI second**: rejected — the index needs no token and answers for every user; the GitHub
  path needs credentials for half of them.

## Consequences
- The trusted publisher has to be registered once on pypi.org by the owner — project `sherpa-harness`,
  owner `sherparc`, repository `Sherpa`, workflow `release.yml`, environment `pypi` — before the first tag
  after this ADR; the README claims the index from that tag on.
- `sherpa doctor` on a fresh machine without any GitHub credentials reports `current (via PyPI)` instead of a
  warning; the `GITHUB_TOKEN` row in the environment table describes the fallback only.
- The wheel on PyPI carries `License-Expression: PolyForm-Small-Business-1.0.0 OR PolyForm-Noncommercial-1.0.0`
  (ADR-0051); PyPI shows both texts from `LICENSE`.
- The version goes to 0.8.0: the first release on the index, under the public licence.
