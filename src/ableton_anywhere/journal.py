"""Action journal: the observability backbone for the GUI and CLI.

Every agent action (tool call) is recorded with its arguments, result, and a
lightweight "state after" snapshot. This is what makes the agent's work
*visible and replayable* instead of a black box — the core differentiator.
"""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_LOG = Path.home() / ".ableton-anywhere" / "journal.jsonl"


@dataclass
class Entry:
    ts: float
    tool: str
    arguments: dict
    ok: bool
    result: str = ""
    error: str = ""
    state_after: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class Journal:
    """Thread-safe, bounded in-memory journal with optional JSONL persistence."""

    def __init__(self, maxlen: int = 500, log_path: Path | None = None) -> None:
        self._entries: deque[Entry] = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._log_path = Path(log_path) if log_path else None

    def record(
        self,
        tool: str,
        arguments: dict | None,
        ok: bool,
        result: str = "",
        error: str = "",
        state_after: dict | None = None,
    ) -> Entry:
        entry = Entry(
            ts=time.time(),
            tool=tool,
            arguments=arguments or {},
            ok=ok,
            result=result,
            error=error,
            state_after=state_after,
        )
        with self._lock:
            self._entries.append(entry)
            self._persist(entry)
        return entry

    def _persist(self, entry: Entry) -> None:
        if not self._log_path:
            return
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry.to_dict()) + "\n")
        except OSError:
            pass  # journaling must never break a tool call

    def recent(self, n: int = 100) -> list[dict]:
        with self._lock:
            return [e.to_dict() for e in list(self._entries)[-n:]]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


# Process-wide default journal. Persistence is opt-in via configure().
journal = Journal()
