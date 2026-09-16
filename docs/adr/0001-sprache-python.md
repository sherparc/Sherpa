# ADR-0001 — Implementierungssprache: Python

**Status:** akzeptiert · **Datum:** 2026-09-16

## Kontext
Sherpa hat drei Stufen: Scanner (deterministisch), Wissensarchitekt (LLM), Applier (deterministisch).
Zur Wahl standen Rust und Python. Auf dem Zielsystem (DGX Spark, Ubuntu 24.04 ARM64) ist Python 3.12
vorhanden, kein `cargo`/`rustc`.

## Entscheidung
Python 3.12, stdlib-first, `src/`-Layout, `sherpa` als Entry-Point.

## Begründung
- Das Vorbild ist Python: `check-harness.py`, Hooks, `outcome.py`, Librarian-Scripts. Sherpa muss diese
  Templates erzeugen **und** ausführen — eine Sprache, ein Testlauf.
- Die Mitte (LLM-Stufe) ist in Python nativ (Anthropic SDK, Claude-Code-Hooks sind Python-Scripts).
- Der Scanner ist nicht rechenintensiv: `git log`, Projektdateien, tree-sitter hat Python-Bindings.
  Bandbreite ist Git, nicht die Sprache.
- Ein Autor, hohe Iterationsgeschwindigkeit. Korrektheit kommt beim Vorbild aus Selftests
  (`selftest-check-harness.py`, 20 Fälle), nicht aus dem Typsystem — das bleibt so.

## Was Rust gebracht hätte
- Ein statisches Binary zur Verteilung (kein venv).
- Compile-Time-Garantien für Modell/Plan/State-Schemata.
- Schnellerer Scanner auf sehr grossen Monorepos.

## Kippkriterium
Rust-Scanner (via PyO3, nicht Rewrite), wenn `sherpa scan` auf einem Zielrepo > 60 s braucht **oder**
die Verteilung an Dritte ohne Python-Umgebung Anforderung wird. Schemata werden ab M1 als JSON-Schema
geführt, damit ein späterer Rust-Kern sie ohne Neudefinition übernimmt.
