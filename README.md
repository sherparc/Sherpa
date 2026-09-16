# Sherpa

Harness-Generator über Repos: ingestieren, planen, nach Freigabe anlegen.

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/sherpa --version
.venv/bin/pytest -q
```

```bash
.venv/bin/sherpa scan /pfad/zum/repo          # → /pfad/zum/repo/.sherpa/codebase-model.json
```

Plan: [docs/plan.md](docs/plan.md) · Scanner: [docs/scan.md](docs/scan.md) · Entscheidungen: [docs/adr/](docs/adr/)
