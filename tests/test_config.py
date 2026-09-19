from pathlib import Path

from sherpa.config import GENERATED_DEFAULT, Config, ScanConfig, load


def test_missing_file_gives_defaults(tmp_path: Path):
    assert load(tmp_path) == Config()
    assert load(tmp_path).scan == ScanConfig(trunk=None, hotspots=20)


def test_partial_config(tmp_path: Path):
    (tmp_path / "sherpa.toml").write_text('[scan]\ntrunk = "origin/dev"\n')
    assert load(tmp_path).scan == ScanConfig(trunk="origin/dev", hotspots=20)


def test_generated_globs_extend_defaults(tmp_path: Path):
    (tmp_path / "sherpa.toml").write_text('[scan]\ngenerated = ["gen/*", "*.tpl"]\n')
    g = load(tmp_path).scan.generated
    assert g[: len(GENERATED_DEFAULT)] == GENERATED_DEFAULT and g[-2:] == ("gen/*", "*.tpl")


def test_unknown_sections_ignored(tmp_path: Path):
    (tmp_path / "sherpa.toml").write_text('[llm]\nprovider = "openai"\n[scan]\nhotspots = 5\n')
    assert load(tmp_path).scan.hotspots == 5


def test_detect_targets_from_the_repository(tmp_path: Path):
    """ADR-0015: `.claude/` or `CLAUDE.md` → claude, `.agents/` or `AGENTS.md` → agents-md, nothing → every target;
    one rule, shared by `apply` and `doctor`."""
    from sherpa.config import TARGETS, detect_targets

    assert detect_targets(tmp_path) == tuple(TARGETS)
    (tmp_path / "AGENTS.md").write_text("# x\n", encoding="utf-8")
    assert detect_targets(tmp_path) == ("agents-md",)
    (tmp_path / "CLAUDE.md").write_text("# x\n", encoding="utf-8")
    assert detect_targets(tmp_path) == ("claude", "agents-md")
    (tmp_path / "AGENTS.md").unlink()
    (tmp_path / ".agents").mkdir()
    assert detect_targets(tmp_path) == ("claude", "agents-md")
