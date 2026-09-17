"""A stdlib validator for the JSON schemas sherpa ships (``sherpa/schemas/*.json``), so a production install checks
its own files the way the test suite does (ADR-0042). It interprets the keyword subset the three schemas use —
``type``, ``enum``, ``const``, ``required``, ``properties``, ``additionalProperties``, ``items``, ``pattern``,
``minimum``, ``maximum`` — and raises ``SchemaError`` with the path and a message shaped like jsonschema's.
``format`` is descriptive here as it is in jsonschema's default validator. The dev extra ``jsonschema`` cross-checks
this validator on the same inputs in the tests; it is never a runtime dependency (stdlib-first)."""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path
from typing import Any

SCHEMAS = Path(__file__).parent / "schemas"

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


class SchemaError(ValueError):
    """``path`` is the JSON-pointer-like location (``entries/3/kind``), ``message`` what is wrong there."""

    def __init__(self, path: list[Any], message: str) -> None:
        self.path, self.message = "/".join(str(p) for p in path), message
        super().__init__(f"{self.path or 'root'}: {message}")


@cache
def load(name: str) -> dict[str, Any]:
    """A shipped schema by file name (``harness-plan.schema.json``), parsed once."""
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def _is_type(value: Any, name: str) -> bool:
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    return isinstance(value, _TYPES[name])


def validate(data: Any, schema: dict[str, Any], path: list[Any] | None = None) -> None:
    """Raise ``SchemaError`` at the first violation, depth-first in document order — one clear line, as pip and
    Terraform report a bad file."""
    path = path or []
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(data, n) for n in names):
            raise SchemaError(path, f"{data!r} is not of type {', '.join(repr(n) for n in names)}")
    if "enum" in schema and data not in schema["enum"]:
        raise SchemaError(path, f"{data!r} is not one of {schema['enum']!r}")
    if "const" in schema and data != schema["const"]:
        raise SchemaError(path, f"{schema['const']!r} was expected")
    if isinstance(data, str) and "pattern" in schema and not re.search(schema["pattern"], data):
        raise SchemaError(path, f"{data!r} does not match {schema['pattern']!r}")
    if _is_type(data, "number"):
        if "minimum" in schema and data < schema["minimum"]:
            raise SchemaError(path, f"{data!r} is less than the minimum of {schema['minimum']!r}")
        if "maximum" in schema and data > schema["maximum"]:
            raise SchemaError(path, f"{data!r} is greater than the maximum of {schema['maximum']!r}")
    if isinstance(data, dict):
        for key in schema.get("required", []):
            if key not in data:
                raise SchemaError(path, f"{key!r} is a required property")
        props = schema.get("properties", {})
        for key, value in data.items():
            if key in props:
                validate(value, props[key], [*path, key])
            elif schema.get("additionalProperties") is False:
                raise SchemaError(path, f"Additional properties are not allowed ({key!r} was unexpected)")
            elif isinstance(schema.get("additionalProperties"), dict):
                validate(value, schema["additionalProperties"], [*path, key])
    if isinstance(data, list) and isinstance(schema.get("items"), dict):
        for i, item in enumerate(data):
            validate(item, schema["items"], [*path, i])
