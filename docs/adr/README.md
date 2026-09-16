# ADRs — Architecture Decision Records

Eine Datei je Entscheidung: Kontext → Entscheidung → Begründung → Konsequenzen. Nie editiert, nur durch ein
neues ADR abgelöst (`Status: ersetzt durch ADR-xxxx`). Nach **jeder Iteration** werden die getroffenen
Entscheidungen hier festgehalten — was kein ADR hat, ist nicht entschieden.

| ADR | Entscheidung | Status |
|---|---|---|
| [0001](0001-sprache-python.md) | Python, stdlib-first; Rust nur bei Kippkriterium | akzeptiert |
| [0002](0002-generisch-vs-spezifisch.md) | Trennung generisch (Template) / Adapter / projekt-only | vorgeschlagen |
| [0003](0003-trunk-erkennung.md) | Scan immer gegen `origin/<trunk>`; Erkennungsreihenfolge | akzeptiert |
| [0004](0004-modell-provider.md) | eigene dünne Provider-Schicht; kein LangChain/LangGraph | akzeptiert |
| [0005](0005-plan-format-und-einchecken.md) | Plan als YAML; Plan + State eingecheckt, Modell nicht | akzeptiert |
| [0006](0006-schwellen-relativ-mit-boden.md) | Schwellen relativ (Perzentil) mit absolutem Boden | akzeptiert |
| [0007](0007-adopt-statt-ueberschreiben.md) | `sherpa adopt` übernimmt bestehende Harnesse, nie überschreiben | akzeptiert |
| [0008](0008-dry-run-default-und-outcome-minimum.md) | `apply`: Dry-Run zuerst; Outcome-Minimum in jedem `apply` | akzeptiert |
