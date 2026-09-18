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
  harness_rev  from .sherpa/state.json when the prompt arrived — the number a harness change has to be measured
            against; ``harness_rev_at_stop`` is added when `sherpa apply` changed it during the execution
  correction   a follow-up prompt that starts with "no, that's wrong" (and friends) relabels the previous
            execution as failed — the cheapest outcome signal there is
  prompt    the first 160 characters of the user prompt, so a label can be read next to what was asked

Privacy: every record stays on this machine — ``.sherpa/telemetry/`` is git-ignored by the file sherpa writes
next to it, nothing is uploaded, and the prompt excerpt is the only free text stored. A team that does not want
prompt text on disk removes the hook entries from ``.claude/settings.json``; ``sherpa status`` then reports no
outcomes, nothing else changes.

Evaluation (labels per harness_rev, trend, share of unknown) is ``sherpa status`` in M5.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

SHERPA_VERSION = "0.7.7"  # replaced on deploy

# A test run is a test runner as the *command word* of a shell segment, not the word anywhere in the line:
# `cat pytest.ini`, `pip install pytest` and `grep jest src/` are not test runs (ADR-0040).
_SEGMENT_RE = re.compile(r"\s*(?:&&|\|\||[;|&\n])\s*")
_PREFIX_RE = re.compile(
    r"^(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+|(?:env|time|sudo|nice|nohup|exec)\s+|(?:uv|poetry|pipenv|pdm|hatch|rye)\s+run\s+"
    r"|(?:bun|pnpm|yarn)\s+exec\s+|(?:npx|bunx|pnpx)\s+)+"
)
_RUNNER_BINARIES = {"pytest", "py.test", "rspec", "phpunit", "jest", "vitest", "mocha", "tox", "nox", "ctest"}
_RUNNER_PHRASES = (
    ("python", "-m", "pytest"),
    ("python3", "-m", "pytest"),
    ("dotnet", "test"),
    ("npm", "test"),
    ("npm", "t"),
    ("pnpm", "test"),
    ("yarn", "test"),
    ("bun", "test"),
    ("go", "test"),
    ("cargo", "test"),
    ("cargo", "nextest"),
    ("mvn", "test"),
    ("mvn", "verify"),
    ("gradle", "test"),
    ("gradlew", "test"),
    ("make", "test"),
    ("make", "check"),
    ("rake", "test"),
    ("mix", "test"),
    ("swift", "test"),
    ("flutter", "test"),
)


def is_test_run(command: str) -> bool:
    """True when any shell segment of ``command`` *starts* with a known test runner (after env assignments and
    wrappers such as ``uv run``); a path before the binary (``.venv/bin/pytest``) is fine, `npm run test*` too."""
    for seg in _SEGMENT_RE.split(command):
        seg = _PREFIX_RE.sub("", seg.strip())
        words = seg.split()
        if not words:
            continue
        words[0] = words[0].rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        if words[0].endswith(".exe"):
            words[0] = words[0][:-4]
        if words[0] in _RUNNER_BINARIES:
            return True
        if len(words) >= 3 and words[0] in ("npm", "pnpm", "yarn") and words[1] == "run":
            if words[2].startswith("test"):
                return True
        for phrase in _RUNNER_PHRASES:
            if tuple(words[: len(phrase)]) == phrase:
                return True
    return False


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
                "harness_rev": self.harness_rev(),  # the harness the agent starts with (ADR-0040)
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
            if is_test_run(cmd):
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
        # The label belongs to the harness the execution started with; an `apply` inside the execution changes
        # the state mid-way, and the end revision is kept next to it so the evaluation can drop such runs.
        at_start = ex.get("harness_rev") or self.harness_rev()
        at_stop = self.harness_rev()
        record = {
            "kind": "outcome",
            "id": ex["id"],
            "ts": int(time.time() * 1000),
            "started": ex["ts"],
            "session_id": self.session,
            "harness_rev": at_start,
            "sherpa": SHERPA_VERSION,
            "label": label,
            "signals": s,
            "prompt": ex["prompt"],
        }
        if at_stop != at_start:
            record["harness_rev_at_stop"] = at_stop
        self.append(record)
        cur["last"] = {"id": ex["id"], "harness_rev": record["harness_rev"]}
        cur["open"] = None
        self.save(cur)


if __name__ == "__main__":
    sys.exit(main())
