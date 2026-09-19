# Contributing to Sherpa

Thank you for looking at the code. Sherpa is small and deliberate; these rules keep it that way and are the
same ones the maintainer works by ([CLAUDE.md](CLAUDE.md) has the long form).

## Before you start

- **Open an issue first** for anything larger than a fix — a new rule, a new host adapter, a change to a
  format. Every design decision in Sherpa is an ADR under [docs/adr/](docs/adr/README.md); what has no ADR is
  not decided, and a pull request that needs one carries it.
- **Licence and DCO.** Sherpa is licensed under PolyForm Small Business or Noncommercial ([LICENSE](LICENSE)).
  Every commit must carry a [Developer Certificate of Origin](https://developercertificate.org/) sign-off —
  `git commit -s`, or once per clone `git config core.hooksPath .githooks` (its `prepare-commit-msg` adds the
  line, its `pre-push` refuses a push to `main`). The `dco` check on the pull request
  refuses a commit without `Signed-off-by:`. The sign-off is your statement that you may contribute the change
  under the repository's licence; there is no CLA.

## The rules that CI enforces

- `.venv/bin/pytest -q --cov=sherpa` green with coverage ≥ 90 %; `.venv/bin/ruff check . && .venv/bin/ruff format --check .` clean.
- Every new function comes with tests; fixture repositories are built in `tests/conftest.py`, never checked in.
- Plan goldens under `tests/goldens/` change only on purpose (`SHERPA_UPDATE_GOLDENS=1`) and the pull request says why.

## The rules a reviewer enforces

- **English everywhere**: code, comments, docs, commit messages, test names.
- **Scanner and applier stay deterministic** — no LLM, no network, no new runtime dependency (PyYAML is the only one).
- **Sherpa never overwrites what exists in a user's repository** — it creates, appends and merges; it rewrites
  only its own bytes between `sherpa:begin`/`sherpa:end` markers or whole files it deployed and nobody changed.
- **Runtime-specific code lives in one adapter each** in `src/sherpa/apply/render.py`; the core stays neutral.
- **Docs move with the code**: the command reference in `docs/commands/`, the concept page, the README when
  the behaviour a user sees changes.
- **No customer or private repository names** anywhere — examples use neutral names such as `Shop.Pricing`.

## The workflow

1. Fork, branch `task/<topic>`, commit with `-s`, one to three full sentences per message.
2. Open the pull request against `main`; the template asks for the ADR and the goldens.
3. Review, then a squash merge by the maintainer. `main` never takes a direct push.

## Development setup

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
.venv/bin/sherpa status .        # the repository carries its own harness; keep it clean
```

Security issues go to [SECURITY.md](SECURITY.md), not to a public issue.
