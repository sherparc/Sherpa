"""The stdlib validator (ADR-0036) against the dev-extra ``jsonschema`` on one input matrix: both must accept the
same documents and reject the same ones at the same location. ``jsonschema`` is the reference, never the runtime."""

from __future__ import annotations

import copy
import json
import sys
from dataclasses import asdict
from pathlib import Path

import jsonschema
import pytest

from sherpa import schema
from sherpa.apply import state as state_mod
from sherpa.cli import main
from sherpa.plan import yamlio
from sherpa.scan import scan
from tests.test_apply import applied


def _set(doc: dict, path: str, value):
    """``entries/0/decision`` → set; value ``schema.DELETE`` removes the key."""
    d = copy.deepcopy(doc)
    parts = path.split("/")
    cur = d
    for p in parts[:-1]:
        cur = cur[int(p)] if isinstance(cur, list) else cur[p]
    key = int(parts[-1]) if isinstance(cur, list) else parts[-1]
    if value is DELETE:
        del cur[key]
    else:
        cur[key] = value
    return d


DELETE = object()

PLAN_CASES = [
    ("entries/0/decision", "rejcet"),
    ("entries/0/decision", "accept "),
    ("entries/0/kind", "wizard"),
    ("entries/0/default", "maybe"),
    ("entries/0/target", DELETE),
    ("entries/0/checks/0", 3),
    ("entries/0/surprise", 1),
    ("schema_version", 999),
    ("schema_version", "1"),
    ("entries", {}),
    ("notes", "one"),
    ("repo", None),
]
STATE_CASES = [("schema_version", 2), ("files", []), ("harness_rev", 12)]
MODEL_CASES = [("schema_version", 4), ("git/trunk/rev", "abc"), ("modules", {})]


@pytest.fixture
def docs(active_repo: Path):
    applied(active_repo)
    plan = yamlio.load(active_repo / ".sherpa" / "harness-plan.yaml")
    state = json.loads((active_repo / ".sherpa" / "state.json").read_text(encoding="utf-8"))
    model = json.loads((active_repo / ".sherpa" / "codebase-model.json").read_text(encoding="utf-8"))
    return {"harness-plan.schema.json": plan, "harness-state.schema.json": state, "codebase-model.schema.json": model}


def _both(name: str, doc: dict):
    """(stdlib error or None, jsonschema error or None) — the pair the matrix compares."""
    ours = ref = None
    try:
        schema.validate(doc, schema.load(name))
    except schema.SchemaError as e:
        ours = e
    try:
        jsonschema.validate(doc, schema.load(name))
    except jsonschema.ValidationError as e:
        ref = e
    return ours, ref


@pytest.mark.parametrize(
    "name", ["harness-plan.schema.json", "harness-state.schema.json", "codebase-model.schema.json"]
)
def test_real_documents_pass_both_validators(docs, name):
    assert _both(name, docs[name]) == (None, None)


@pytest.mark.parametrize(
    "name,path,value",
    [("harness-plan.schema.json", *c) for c in PLAN_CASES]
    + [("harness-state.schema.json", *c) for c in STATE_CASES]
    + [("codebase-model.schema.json", *c) for c in MODEL_CASES],
)
def test_broken_documents_fail_both_validators_at_the_same_place(docs, name, path, value):
    ours, ref = _both(name, _set(docs[name], path, value))
    assert ours is not None and ref is not None, f"{path}={value!r} accepted"
    assert ours.path == "/".join(str(p) for p in ref.absolute_path)


def test_validator_messages_read_like_jsonschema():
    s = {
        "type": "object",
        "required": ["a"],
        "properties": {
            "a": {"enum": [1, 2]},
            "n": {"type": "integer", "minimum": 0, "maximum": 9},
            "p": {"type": "string", "pattern": "^x"},
            "c": {"const": 4},
        },
        "additionalProperties": False,
    }
    for doc, needle in [
        ({}, "'a' is a required property"),
        ({"a": 3}, "3 is not one of [1, 2]"),
        ({"a": 1, "n": -1}, "-1 is less than the minimum of 0"),
        ({"a": 1, "n": 10}, "10 is greater than the maximum of 9"),
        ({"a": 1, "n": True}, "True is not of type 'integer'"),
        ({"a": 1, "p": "y"}, "'y' does not match '^x'"),
        ({"a": 1, "c": 5}, "4 was expected"),
        ({"a": 1, "z": 0}, "Additional properties are not allowed ('z' was unexpected)"),
    ]:
        with pytest.raises(schema.SchemaError) as e:
            schema.validate(doc, s)
        assert needle in str(e.value)
    schema.validate({"a": 1, "n": 9, "p": "xy", "c": 4}, s)
    schema.validate(
        {"k": [1, "a"]}, {"additionalProperties": {"type": "array", "items": {"type": ["integer", "string"]}}}
    )
    with pytest.raises(schema.SchemaError, match="k/1: 2.5 is not of type 'integer', 'string'"):
        schema.validate(
            {"k": [1, 2.5]}, {"additionalProperties": {"type": "array", "items": {"type": ["integer", "string"]}}}
        )


def test_apply_refuses_a_typo_in_a_decision_without_jsonschema(active_repo: Path, capsys, monkeypatch):
    """The finding: ``decision: rejcet`` passed ``plan_from_dict`` on a production install and ``selected()`` treated
    it as not rejected — the agent the human refused was rendered. Now every reader validates with the stdlib."""
    monkeypatch.setitem(sys.modules, "jsonschema", None)  # a wheel install: no dev extra
    applied(active_repo)
    pp = active_repo / ".sherpa" / "harness-plan.yaml"
    text = pp.read_text(encoding="utf-8")
    pp.write_text(text.replace("decision: null", "decision: rejcet", 1), encoding="utf-8")
    for cmd in ("apply", "status", "adopt"):
        assert main([cmd, str(active_repo), *(["--yes"] if cmd == "apply" else [])]) == 1
        assert "harness-plan.yaml invalid at entries/0/decision: 'rejcet' is not one of" in capsys.readouterr().err
    pp.write_text(text.replace("schema_version: 1", "schema_version: 999", 1), encoding="utf-8")
    assert main(["status", str(active_repo)]) == 1
    assert "invalid at schema_version: 1 was expected" in capsys.readouterr().err
    pp.write_text(text.replace("kind: agent", "kind: wizard", 1), encoding="utf-8")
    assert main(["apply", str(active_repo), "--dry-run"]) == 1
    assert "'wizard' is not one of" in capsys.readouterr().err
    pp.write_text(text, encoding="utf-8")
    assert main(["status", str(active_repo)]) == 0


def test_scan_and_state_validate_with_the_stdlib(active_repo: Path, monkeypatch):
    monkeypatch.setitem(sys.modules, "jsonschema", None)
    from sherpa import model as model_mod

    model_mod.validate(asdict(scan(active_repo, fetch=False)))
    with pytest.raises(ValueError, match="model invalid at schema_version"):
        model_mod.validate(_set(asdict(scan(active_repo, fetch=False)), "schema_version", 1))
    applied(active_repo)
    state = json.loads((active_repo / ".sherpa" / "state.json").read_text(encoding="utf-8"))
    state_mod.validate(state)
    with pytest.raises(ValueError, match="state invalid at files"):
        state_mod.validate(_set(state, "files", []))
