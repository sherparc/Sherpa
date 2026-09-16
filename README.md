# Sherpa

Harness-Generator über Repos: ingestieren, planen, nach Freigabe anlegen.

Stand: `sherpa scan` liefert T0 (Git: Trunk, Churn, Hotspots) und T1 (Module aus Manifesten für .NET, Python,
Node, Go, Rust, Java mit repo-internen Abhängigkeiten). `plan`/`apply`/`status` folgen (M2+).

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/sherpa --version
.venv/bin/pytest -q
```

```bash
.venv/bin/sherpa scan /pfad/zum/repo          # → /pfad/zum/repo/.sherpa/codebase-model.json
```

Plan: [docs/plan.md](docs/plan.md) · Scanner: [docs/scan.md](docs/scan.md) · Entscheidungen: [docs/adr/](docs/adr/)
