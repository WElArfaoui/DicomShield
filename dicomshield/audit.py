from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass 
class AuditRecord:
    """Audit record for a processed file."""

    input_path: str
    output_path: str
    status: str
    changes: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    def to_json(self) -> str:
        payload = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "input_path": self.input_path,
            "output_path": self.output_path,
            "status": self.status,
            "changes": self.changes,
            "warnings": self.warnings,
            "error": self.error,
        }
        return json.dumps(payload, ensure_ascii=True)


def append_audit_line(audit_file: Path, record: AuditRecord) -> None:
    """Append a JSON line (jsonl) to the audit file."""
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    with audit_file.open("a", encoding="utf-8") as f:
        f.write(record.to_json() + "\n")
