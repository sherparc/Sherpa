#!/usr/bin/env python3
"""sherpa outcome hook — one label per execution, stamped with the harness version (ADR-0008).

Installed by ``sherpa apply`` as ``.claude/hooks/sherpa-outcome.py`` and wired into ``.claude/settings.json`` for
UserPromptSubmit, PostToolUse (Bash|Edit|Write|MultiEdit), PostToolUseFailure (Bash) and Stop. Stdlib only,
fail-open: it never blocks a prompt, never prints to stdout (UserPromptSubmit output would land in the context)
and swallows every error.

What it records, per execution (= one user prompt until the next Stop), in ``.sherpa/telemetry/outcomes.ndjson``:

  label     success | failed | unknown
            success: the last test run was green, or a pull request was created
            failed:  the last test run was red
            unknown: no signal — a pure question/answer turn; honest, not bad
  signals   bash/edit counts, test runs and failures, pushed, pr_created, stop_failure
  harness_rev  from .sherpa/state.json — the number a harness change has to be measured against
  correction   a follow-up prompt that starts with "no, that's wrong" (and friends) relabels the previous
            execution as failed — the cheapest outcome signal there is

Evaluation (labels per harness_rev, trend, share of unknown) is ``sherpa status`` in M5.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

SHERPA_VERSION = "0.5.0"  # replaced on deploy

TEST_RE = re.compile(
    r"\b(pytest|python -m pytest|dotnet test|npm test|npm run test|pnpm test|yarn test|go test|cargo test|"
    r"mvn (test|verify)|gradle(w)? test|rspec|phpunit|jest|vitest)\b"
)
PR_RE = re.compile(r"\b(gh pr create|glab mr create|az repos pr create)\b")
PUSH_RE = re.compile(r"\bgit push\b")
CORRECTION_RE = re.compile(
    r"^\s*(no[,.! ]|nope|wrong|that'?s (wrong|not right|incorrect)|not correct|doesn'?t work|does not work|"
    r"still (broken|failing|wrong)|nein[,.! ]|falsch)",
    re.I,
)
ZERO = {
    "bash": 0,
    "bash_errors": 0,
    "edits": 0,
    "tests_run": 0,
    "tests_failed": 0,
    "last_test": None,
    "pushed": False,
    "pr_created": False,
}


def main() -> int:
    try:
        event = json.load(sys.stdin)
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or ".")
        Hook(root, event).run()
    except Exception:  # noqa: BLE001 — fail-open by design
        pass
    return 0


class Hook:
    def __init__(self, root: Path, event: dict) -> None:
        self.root, self.event = root, event
        self.dir = root / ".sherpa" / "telemetry"
        self.session = str(event.get("session_id") or "unknown")
        self.current_path = self.dir / f"session-{self.session}.json"

    def run(self) -> None:
        name = self.event.get("hook_event_name")
        if name == "UserPromptSubmit":
            self.start(str(self.event.get("prompt") or ""))
        elif name in ("PostToolUse", "PostToolUseFailure"):
            self.tool(name == "PostToolUseFailure")
        elif name == "Stop":
            self.stop()

    # ------------------------------------------------------------ state per session

    def load(self) -> dict | None:
        try:
            return json.loads(self.current_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def save(self, cur: dict | None) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        if cur is None:
            self.current_path.unlink(missing_ok=True)
        else:
            self.current_path.write_text(json.dumps(cur), encoding="utf-8")

    def append(self, record: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with (self.dir / "outcomes.ndjson").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def harness_rev(self) -> str:
        try:
            return str(json.loads((self.root / ".sherpa" / "state.json").read_text(encoding="utf-8"))["harness_rev"])
        except (OSError, ValueError, KeyError):
            return "none"

    # ------------------------------------------------------------ events

    def start(self, prompt: str) -> None:
        cur = self.load() or {}
        prev = cur.get("last")  # the previous execution of this session, already labelled at its Stop
        if prev and CORRECTION_RE.match(prompt):
            self.append(
                {
                    "kind": "correction",
                    "ts": int(time.time() * 1000),
                    "session_id": self.session,
                    "execution": prev["id"],
                    "label": "failed",
                    "harness_rev": prev.get("harness_rev"),
                }
            )
        n = int(cur.get("n", 0)) + 1
        cur = {
            "n": n,
            "last": prev,
            "open": {
                "id": f"{self.session}:{n}",
                "ts": int(time.time() * 1000),
                "prompt": prompt[:160],
                "signals": dict(ZERO),
            },
        }
        self.save(cur)

    def tool(self, failed: bool) -> None:
        cur = self.load()
        if not cur or not cur.get("open"):
            return
        s = cur["open"]["signals"]
        tool = str(self.event.get("tool_name") or "")
        if tool == "Bash":
            cmd = str((self.event.get("tool_input") or {}).get("command") or "")
            s["bash"] += 1
            if failed:
                s["bash_errors"] += 1
            if TEST_RE.search(cmd):
                s["tests_run"] += 1
                if failed:
                    s["tests_failed"] += 1
                s["last_test"] = "red" if failed else "green"
            if not failed and PR_RE.search(cmd):
                s["pr_created"] = True
            if not failed and PUSH_RE.search(cmd):
                s["pushed"] = True
        elif tool in ("Edit", "Write", "MultiEdit"):
            s["edits"] += 1
        self.save(cur)

    def stop(self) -> None:
        cur = self.load()
        if not cur or not cur.get("open"):
            return
        ex = cur["open"]
        s = ex["signals"]
        if s["last_test"] == "red":
            label = "failed"
        elif s["last_test"] == "green" or s["pr_created"]:
            label = "success"
        else:
            label = "unknown"
        record = {
            "kind": "outcome",
            "id": ex["id"],
            "ts": int(time.time() * 1000),
            "started": ex["ts"],
            "session_id": self.session,
            "harness_rev": self.harness_rev(),
            "sherpa": SHERPA_VERSION,
            "label": label,
            "signals": s,
            "prompt": ex["prompt"],
        }
        self.append(record)
        cur["last"] = {"id": ex["id"], "harness_rev": record["harness_rev"]}
        cur["open"] = None
        self.save(cur)


if __name__ == "__main__":
    sys.exit(main())
