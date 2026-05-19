"""Pipeline audit logging."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AuditLogger:
    """Writes JSONL audit events for framework runs."""

    def __init__(self, audit_path: str | Path) -> None:
        self.audit_path = Path(audit_path)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "logged_at": datetime.now(UTC).isoformat(),
            "rejected_record_count": 0,
            "warning_count": 0,
            "error_message": "",
            **event,
        }
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return payload


def read_audit_events(audit_path: str | Path) -> list[dict[str, Any]]:
    """Read audit events from a JSONL audit file."""
    path = Path(audit_path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
