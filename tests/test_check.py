"""``sherpa check``: block grammar, front matter subset, rules C1–C8, standalone copy and delegation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from sherpa import check
from sherpa.check import FAIL, WARN, block_contents, content_hash, front_matter, parse_blocks

# ---------------------------------------------------------------- primitives


def test_content_hash_ignores_line_endings():
    assert content_hash("a\r\nb\r\n") == content_hash("a\nb\n")
    assert len(content_hash("x")) == 16


def test_parse_blocks_html_and_yaml_markers():
    text = "---\n# sherpa:begin k\nknowledge: []\n# sherpa:end k\n---\n<!-- sherpa:begin f -->\nx\ny\n<!-- sherpa:end f -->\n"
    assert parse_blocks(text) == {"k": (1, 3), "f": (5, 8)}
    assert block_contents(text) == {"k": "knowledge: []", "f": "x\ny"}


@pytest.mark.parametrize(
    "text, msg",
    [
        ("<!-- sherpa:begin a -->\nx\n", "never closed"),
        ("<!-- sherpa:end a -->\n", "without matching begin"),
        ("<!-- sherpa:begin a -->\n<!-- sherpa:end b -->\n", "without matching begin"),
        ("<!-- sherpa:begin a -->\n<!-- sherpa:begin b -->\n", "inside open block a"),
        (
            "<!-- sherpa:begin a -->\n<!-- sherpa:end a -->\n<!-- sherpa:begin a -->\n<!-- sherpa:end a -->\n",
            "duplicate",
        ),
    ],
)
def test_parse_blocks_rejects_broken_markers(text, msg):
    with pytest.raises(ValueError, match=msg):
        parse_blocks(text)


def test_front_matter_subset():
    fm = front_matter(
        '---\nname: pay\ndescription: "Use this agent"  # trailing\n# a comment line\nknowledge:\n'
        "  always:\n    - docs/modules/pay.md\n  on_demand: []\nmodel: sonnet\n---\n# body\n"
    )
    assert fm == {
        "name": "pay",
        "description": "Use this agent",
        "knowledge": {"always": ["docs/modules/pay.md"], "on_demand": []},
        "model": "sonnet",
    }
    assert front_matter("# no front matter\n") is None
    assert front_matter("---\ntags:\n  - a\n  - b\n---\n") == {"tags": ["a", "b"]}


# ---------------------------------------------------------------- rules


def harness(root: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")


GOOD_AGENT = "---\nname: pay\ndescription: x\nknowledge:\n  always:\n    - docs/modules/pay.md\n---\n# pay\n[doc](../docs/modules/pay.md)\n"


def test_clean_harness_has_no_findings(tmp_path: Path):
    harness(
        tmp_path,
        {
            ".claude/agents/pay.md": GOOD_AGENT,
            ".claude/docs/modules/pay.md": "# pay\n<!-- sherpa:begin facts -->\nx\n<!-- sherpa:end facts -->\n",
            ".claude/skills/s/SKILL.md": "---\nname: s\ndescription: d\n---\n# s\n",
            ".claude/settings.json": json.dumps(
                {
                    "hooks": {
                        "Stop": [
                            {
                                "hooks": [
                                    {"type": "command", "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/h.py"'}
                                ]
                            }
                        ]
                    }
                }
            ),
            ".claude/hooks/h.py": "",
            "CLAUDE.md": "# repo\n[plan](docs/plan.md) [ext](https://x.y) [anchor](#top) [mail](mailto:a@b) [wiki](Wiki/Page)\n",
            ".claude/docs/archive/old.md": "[gone](../nope.md)\n",
            "docs/plan.md": "",
        },
    )
    assert check.check(tmp_path) == []


def test_rules_c1_to_c6(tmp_path: Path):
    harness(
        tmp_path,
        {
            ".claude/agents/a.md": "# no front matter\n",
            ".claude/agents/b.md": "---\nname: b\nknowledge:\n  always:\n    - docs/modules/missing.md\n---\n[x](../nope.md)\n",
            ".claude/skills/s/SKILL.md": "---\ndescription: d\n---\n",
            ".claude/docs/modules/m.md": "<!-- sherpa:begin f -->\nopen\n",
            ".claude/settings.json": json.dumps(
                {"hooks": {"Stop": [{"hooks": [{"command": 'sh "${CLAUDE_PROJECT_DIR}/.claude/hooks/gone.py"'}]}]}}
            ),
        },
    )
    got = {(f.rule, f.path, f.message) for f in check.check(tmp_path)}
    assert got == {
        ("C1", ".claude/agents/a.md", "no front matter (name, description required)"),
        ("C1", ".claude/agents/b.md", "front matter has no description"),
        ("C3", ".claude/agents/b.md", "knowledge path docs/modules/missing.md does not exist"),
        ("C4", ".claude/agents/b.md", "link target ../nope.md does not exist"),
        ("C2", ".claude/skills/s/SKILL.md", "front matter has no name"),
        ("C5", ".claude/docs/modules/m.md", "managed block markers: block f is never closed"),
        ("C6", ".claude/settings.json", "Stop hook references missing file .claude/hooks/gone.py"),
    }
    assert all(f.level == FAIL for f in check.check(tmp_path))


def test_invalid_settings_json_is_a_fail(tmp_path: Path):
    harness(tmp_path, {".claude/settings.json": "{not json"})
    (f,) = check.check(tmp_path)
    assert (f.level, f.rule) == (FAIL, "C6") and "not valid JSON" in f.message


def test_c7_budgets_warn(tmp_path: Path):
    harness(tmp_path, {".claude/agents/fat.md": "---\nname: f\ndescription: d\n---\n" + "line\n" * 160})
    (f,) = check.check(tmp_path)
    assert (f.level, f.rule) == (WARN, "C7") and "> budget 150 (agent)" in f.message


def test_c8_drift_against_state(tmp_path: Path):
    doc = "# m\n<!-- sherpa:begin facts -->\nv1\n<!-- sherpa:end facts -->\n"
    harness(
        tmp_path,
        {
            ".claude/docs/modules/m.md": doc.replace("v1", "edited"),
            ".claude/docs/modules/n.md": "# n\n",
            ".claude/hooks/h.py": "changed\n",
            ".sherpa/state.json": json.dumps(
                {
                    "files": {
                        ".claude/docs/modules/m.md": {
                            "mode": "blocks",
                            "blocks": {"facts": content_hash("v1"), "gone": "0" * 16},
                        },
                        ".claude/docs/modules/n.md": {"mode": "blocks", "blocks": {}},
                        ".claude/hooks/h.py": {"mode": "managed", "hash": content_hash("orig\n")},
                        ".claude/missing.md": {"mode": "managed", "hash": "0" * 16},
                    }
                }
            ),
        },
    )
    got = sorted((f.level, f.path, f.message) for f in check.check(tmp_path))
    assert got == [
        (WARN, ".claude/docs/modules/m.md", "block facts hand-edited"),
        (WARN, ".claude/docs/modules/m.md", "block gone removed"),
        (WARN, ".claude/hooks/h.py", "hand-edited (hash differs from state)"),
        (WARN, ".claude/missing.md", "missing (in state, not on disk)"),
    ]


def test_render_and_main(tmp_path: Path, capsys):
    harness(tmp_path, {".claude/agents/a.md": "x\n"})
    assert check.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert out.startswith(f"sherpa check {tmp_path.resolve()}: 1 FAIL, 0 WARN\n  FAIL C1 .claude/agents/a.md")
    assert check.main([str(tmp_path), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)[0]["rule"] == "C1"
    (tmp_path / ".claude/agents/a.md").unlink()
    assert check.main([str(tmp_path)]) == 0


# ---------------------------------------------------------------- the deployed copy


def test_deployed_copy_runs_standalone_and_delegates(tmp_path: Path):
    """The copy is the same file; standalone it must not import sherpa, otherwise it defers to the install."""
    copy = tmp_path / ".claude" / "scripts" / "sherpa-check.py"
    copy.parent.mkdir(parents=True)
    copy.write_text(Path(check.__file__).read_text(encoding="utf-8"), encoding="utf-8")
    harness(tmp_path, {".claude/agents/a.md": "x\n"})
    env = {**os.environ, "SHERPA_CHECK_STANDALONE": "1", "PYTHONPATH": ""}
    r = subprocess.run([sys.executable, "-I", str(copy), str(tmp_path)], capture_output=True, text=True, env=env)
    assert r.returncode == 1 and "FAIL C1" in r.stdout and "Traceback" not in r.stderr
    src = Path(__file__).parent.parent / "src"
    env = {**os.environ, "PYTHONPATH": str(src)}
    env.pop("SHERPA_CHECK_STANDALONE", None)
    r = subprocess.run([sys.executable, str(copy), str(tmp_path)], capture_output=True, text=True, env=env)
    assert r.returncode == 1 and "FAIL C1" in r.stdout
