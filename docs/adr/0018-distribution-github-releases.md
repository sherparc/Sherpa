# ADR-0018 — Distribution through GitHub Releases: wheel per tag, `self-update`, a daily hint that never blocks

**Status:** accepted · **Date:** 2026-09-17 · **Decision:** Andrei (§6 Q5) · **§5 taken by:** ADR-0053 (PyPI is the index, 2026-09-19)

## Context
Until M2b a customer installed sherpa with `uv tool install git+https://…` from `main`: no versions, no way to
know that a newer sherpa exists, no `doctor` for the first contact. The repository is private until the public
release (ADR-0010), which rules out PyPI for now. The options were a private package index (Cloudsmith, Gemfury —
a third service with its own token and free-tier limits), a static simple index in the repository (works with
`uv` only through raw URLs with the token embedded), or GitHub Releases through the API with the token every
user with repository access already has.

## Decision
1. **A release is a tag.** `v<version>` pushed to `sherparc/Sherpa` runs `release.yml`: the tag must equal the
   version in `pyproject.toml` and `src/sherpa/__init__.py`, tests and lint run, `python -m build` produces the
   wheel and sdist, the wheel is installed into a fresh venv and `sherpa --version` and `doctor` run, then
   `gh release create` attaches both files with generated notes. What ships is exactly `src/sherpa/` plus the
   schemas and the hook asset (`pyproject.toml` owns the list); tests, docs, the repository's own harness and
   the vault sync are development only.
2. **`sherpa self-update`** reads `releases/latest` through the API with a token from `GITHUB_TOKEN`,
   `GH_TOKEN` or `gh auth token`, downloads the wheel and installs it with the installer that owns the running
   copy (`uv tool install --force --reinstall`, `pipx install --force`, `pip install --upgrade`). Without a
   token, or without a wheel on the release, the source is the tag's git URL — the user's git credentials work
   where the API token does not (the tag itself comes from `git ls-remote`, ADR-0035). An editable clone is
   refused with `git pull` as the fix.
3. **The daily hint never blocks.** The everyday commands start a daemon thread at most once per 24 hours;
   it writes the result to `update-check.json` in the user's cache directory. The command prints only what an
   earlier check cached, on stderr, after its own output, only on a terminal and never under `CI`,
   `SHERPA_NO_UPDATE_CHECK=1`, or for `doctor`, `self-update` and `check` (hooks run `check`). The first run of a
   day therefore never hints; the second does. The switch is documented in the hint line itself.
4. **`sherpa doctor`** is the first command: Python, git, install kind, repository, `origin`, `sherpa.toml`,
   trunk (ADR-0003), runtime, update — each with a level (`✓`, `!`, `✗`) and a fix; exit 1 only on a `✗`.
   Version comparison is numeric with a pre-release suffix sorting below the plain version — enough for our
   tags, deliberately not a PEP 440 parser.
5. **PyPI at the public release.** `sherpa-harness` is reserved as the name (ADR-0009); when the licence flips
   (ADR-0010) `release.yml` gains a publish step and `self-update` switches to the index — the API client is one
   function.

## Reasoning
- No third service: every user who can clone the repository can read its releases with the same token.
- The git URL fallback means the update path works on a machine that has git credentials but no `gh` — the
  normal state of a developer laptop.
- A background thread plus a cache is what `uv`, `pip` and `npm` do; a synchronous check would add up to the
  timeout to every command once a day, and "the hint never blocks" is the acceptance criterion in the plan.
- A refused editable clone protects the development setup: `pip install --upgrade` into a clone's venv would
  replace the editable link with a wheel and the next `git pull` would change nothing visible.

## Consequences
- Releasing is `git tag v0.5.0 && git push origin v0.5.0` after the version bump landed on `main`; the workflow
  refuses a mismatch instead of shipping a wrong version.
- Two more modules in the core (`doctor.py`, `update.py`), stdlib only; tests mock `urllib` and the
  conftest sets `SHERPA_NO_UPDATE_CHECK` so no test reaches the network.
- Open: a signed wheel (Sigstore) and a checksum in the release notes once the release is public.
