"""Metadata access helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MetadataReader:
    """Reads framework metadata from the configured metadata seed."""

    def __init__(self, metadata_path: str | Path) -> None:
        self.metadata_path = Path(metadata_path)
        self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))

    def list_active_datasets(
        self,
        dataset_id: str | None = None,
        dataset_group: str | None = None,
    ) -> list[dict[str, Any]]:
        datasets = [dataset for dataset in self.metadata["datasets"] if dataset.get("active_flag")]
        if dataset_id:
            datasets = [dataset for dataset in datasets if dataset["dataset_id"] == dataset_id]
        if dataset_group:
            datasets = [dataset for dataset in datasets if dataset.get("dataset_group") == dataset_group]
        return datasets

    def read_dataset(self, dataset_id: str) -> dict[str, Any]:
        for dataset in self.metadata["datasets"]:
            if dataset["dataset_id"] == dataset_id:
                return dataset
        raise KeyError(f"Dataset not found: {dataset_id}")

    def read_source(self, dataset_id: str) -> dict[str, Any]:
        return self._read_active("dataset_sources", dataset_id)

    def read_target(self, dataset_id: str) -> dict[str, Any]:
        return self._read_active("dataset_targets", dataset_id)

    def metadata_version(self) -> str:
        return self.metadata.get("metadata_version", "unknown")

    def _read_active(self, collection: str, dataset_id: str) -> dict[str, Any]:
        for row in self.metadata[collection]:
            if row["dataset_id"] == dataset_id and row.get("active_flag"):
                return row
        raise KeyError(f"Active {collection} row not found for dataset: {dataset_id}")
