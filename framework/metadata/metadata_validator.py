"""Metadata validation helpers."""

from __future__ import annotations


class MetadataValidator:
    """Validates metadata records before orchestration."""

    REQUIRED_DATASET_FIELDS = ("dataset_id", "dataset_name", "source_system_id", "load_type")
    REQUIRED_SOURCE_FIELDS = ("dataset_id", "source_object_type", "source_path", "source_format")
    REQUIRED_TARGET_FIELDS = ("dataset_id", "target_platform", "target_path", "write_mode")

    def validate_ingestion_metadata(
        self,
        dataset: dict,
        source: dict,
        target: dict,
    ) -> list[str]:
        errors: list[str] = []
        errors.extend(self._missing("dataset", dataset, self.REQUIRED_DATASET_FIELDS))
        errors.extend(self._missing("source", source, self.REQUIRED_SOURCE_FIELDS))
        errors.extend(self._missing("target", target, self.REQUIRED_TARGET_FIELDS))
        if source.get("dataset_id") != dataset.get("dataset_id"):
            errors.append("source.dataset_id does not match dataset.dataset_id")
        if target.get("dataset_id") != dataset.get("dataset_id"):
            errors.append("target.dataset_id does not match dataset.dataset_id")
        return errors

    def validate(self, metadata: dict) -> list[str]:
        required = metadata.get("required_fields", [])
        payload = metadata.get("payload", {})
        return self._missing("metadata", payload, required)

    def _missing(self, label: str, row: dict, fields: tuple[str, ...] | list[str]) -> list[str]:
        return [f"{label}.{field} is required" for field in fields if row.get(field) in (None, "")]
