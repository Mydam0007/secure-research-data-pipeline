"""One audit event per pipeline stage, written to a JSONL log. Only row
counts and timestamps, never participant values, so the log is safe to
keep next to the de-identified export.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class AuditLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = str(uuid.uuid4())
        self.started_at = datetime.now(timezone.utc).isoformat()

    def event(self, stage: str, rows_in: int, rows_out: int, **details) -> None:
        record = {
            "run_id": self.run_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "rows_in": int(rows_in),
            "rows_out": int(rows_out),
            "details": details,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
