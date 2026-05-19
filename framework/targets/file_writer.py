"""File target writer."""

from __future__ import annotations

import csv
from pathlib import Path

from framework.targets.target_writer import TargetWriter


class FileWriter(TargetWriter):
    """Writes rows to file-based targets."""

    def __init__(self, dataset_root: str | Path) -> None:
        self.dataset_root = Path(dataset_root)

    def write(self, data: list[dict], metadata: dict) -> Path:
        target_path = self.dataset_root / metadata["path"].lstrip("/")
        if metadata.get("write_mode") == "overwrite" and target_path.exists():
            target_path.unlink()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        columns = list(data[0].keys()) if data else metadata.get("expected_columns", [])
        with target_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(data)
        return target_path
