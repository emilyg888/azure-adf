"""Landing zone validation helpers."""

from __future__ import annotations

import csv
from pathlib import Path

from framework.ingestion.source_reader import DELIMITERS


class LandingValidator:
    """Validates files and records in the landing zone."""

    def __init__(self, dataset_root: str | Path) -> None:
        self.dataset_root = Path(dataset_root)

    def validate_landing(
        self,
        run_id: str,
        dataset_id: str,
        target: dict,
        source_record_count: int | None = None,
    ) -> dict:
        target_path = self.dataset_root / target["target_path"].lstrip("/")
        if not target_path.exists():
            raise FileNotFoundError(f"Target path does not exist: {target_path}")

        delimiter = DELIMITERS.get(target.get("target_delimiter", "tab"), "\t")
        with target_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle, delimiter=delimiter))
        target_record_count = max(len(rows) - 1, 0)
        warnings = []
        if target_record_count == 0:
            warnings.append("target row count is zero")
        if source_record_count is not None and source_record_count != target_record_count:
            warnings.append("source and target row counts do not match")

        return {
            "run_id": run_id,
            "dataset_id": dataset_id,
            "validation_status": "PASSED" if not warnings else "PASSED_WITH_WARNINGS",
            "source_record_count": source_record_count,
            "target_record_count": target_record_count,
            "warnings": warnings,
        }

    def validate(self, landing_path: str) -> list[str]:
        path = self.dataset_root / landing_path.lstrip("/")
        return [] if path.exists() else [f"Target path does not exist: {path}"]
