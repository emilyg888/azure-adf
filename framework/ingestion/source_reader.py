"""Source system reader abstractions."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path


DELIMITERS = {
    "comma": ",",
    "csv": ",",
    "tab": "\t",
    "tsv": "\t",
    "pipe": "|",
}


class SourceReader:
    """Reads and copies file-based source data according to dataset metadata."""

    def __init__(self, dataset_root: str | Path) -> None:
        self.dataset_root = Path(dataset_root)

    def resolve(self, metadata_path: str) -> Path:
        relative_path = metadata_path.lstrip("/")
        return self.dataset_root / relative_path

    def read_count(self, source: dict) -> int:
        source_path = self.resolve(source["source_path"])
        if not source_path.exists():
            raise FileNotFoundError(f"Source path does not exist: {source_path}")
        delimiter = DELIMITERS.get(source.get("source_delimiter", "comma"), ",")
        with source_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle, delimiter=delimiter))
        return max(len(rows) - 1, 0)

    def copy_to_target(self, source: dict, target: dict) -> Path:
        source_path = self.resolve(source["source_path"])
        target_path = self.resolve(target["target_path"])
        if not source_path.exists():
            raise FileNotFoundError(f"Source path does not exist: {source_path}")
        if target.get("write_mode") == "overwrite" and target_path.exists():
            target_path.unlink()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        return target_path

    def read(self, metadata: dict):
        return self.resolve(metadata["source_path"])
