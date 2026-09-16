"""``.sherpa/state.json`` — what sherpa owns in the repo and the hash it wrote (ADR-0008, ADR-0013).

One record per file. ``mode`` says how much of the file is sherpa's: ``managed`` = the whole file (hash),
``blocks`` = only the marked blocks (one hash per block), ``json-hooks`` = the hook entries sherpa merged into
``.claude/settings.json``. ``origin`` is ``generated`` or, after ``sherpa adopt``, ``adopted``.

``harness_rev`` is the hash over everything sherpa owns (paths and content hashes) plus the sherpa version — the
outcome hook stamps it on every label, so harness versions can be compared later (M5). Timestamps live only here,
never in generated files (determinism, docs/plan.md §2.3).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sherpa import __version__

STATE_SCHEMA_VERSION = 1
STATE_PATH = Path(".sherpa") / "state.json"
SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "harness-state.schema.json"
MANAGED, BLOCKS, JSON_HOOKS = "managed", "blocks", "json-hooks"
GENERATED, ADOPTED = "generated", "adopted"


@dataclass(frozen=True)
class FileRecord:
    mode: str  # managed | blocks | json-hooks
    origin: str = GENERATED  # generated | adopted
    entry: str | None = None  # "kind/target/scope" of the plan entry, None for base files
    hash: str | None = None  # managed and json-hooks: hash of the whole file
    blocks: dict[str, str] = field(default_factory=dict)  # blocks: name → hash of the inner text


@dataclass
class State:
    harness_rev: str = ""
    plan: dict[str, str] = field(default_factory=dict)  # trunk, rev, as_of of the applied plan
    applied_at: str = ""  # ISO-8601 UTC of the last write; the only clock in the whole apply
    files: dict[str, FileRecord] = field(default_factory=dict)  # repo-relative "/" paths, sorted on write
    sherpa: str = __version__
    schema_version: int = STATE_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "sherpa": self.sherpa,
            "harness_rev": self.harness_rev,
            "plan": dict(self.plan),
            "applied_at": self.applied_at,
            "files": {k: _record_dict(v) for k, v in sorted(self.files.items())},
        }

    def dumps(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.dumps(), encoding="utf-8", newline="\n")

    @classmethod
    def from_dict(cls, d: dict) -> State:
        if d.get("schema_version") != STATE_SCHEMA_VERSION:
            raise ValueError(f"state has schema_version {d.get('schema_version')}, expected {STATE_SCHEMA_VERSION}")
        files = {k: FileRecord(**v) for k, v in d.get("files", {}).items()}
        return cls(d.get("harness_rev", ""), dict(d.get("plan", {})), d.get("applied_at", ""), files, d["sherpa"], 1)


def _record_dict(r: FileRecord) -> dict:
    d = asdict(r)
    if not d["blocks"]:
        del d["blocks"]
    if d["hash"] is None:
        del d["hash"]
    if d["entry"] is None:
        del d["entry"]
    return d


def load(path: Path) -> State:
    return State.from_dict(json.loads(path.read_text(encoding="utf-8")))


def harness_rev(files: dict[str, FileRecord], version: str = __version__) -> str:
    """12 hex chars over everything sherpa owns — changes exactly when a managed file or block changes."""
    h = hashlib.sha256()
    for path, rec in sorted(files.items()):
        h.update(f"{path} {rec.hash or ''}\n".encode())
        for name, bh in sorted(rec.blocks.items()):
            h.update(f"{path}#{name} {bh}\n".encode())
    h.update(f"sherpa {version}\n".encode())
    return h.hexdigest()[:12]


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate(data: dict) -> None:
    """JSON-schema validation when ``jsonschema`` is installed (dev extra); otherwise no-op."""
    try:
        import jsonschema  # type: ignore
    except ImportError:  # pragma: no cover
        return
    jsonschema.validate(data, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
