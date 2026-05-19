"""Target writer abstraction."""

from __future__ import annotations


class TargetWriter:
    """Base target writer interface."""

    def write(self, data, metadata: dict) -> None:
        raise NotImplementedError("Implement target write.")


def write_target(rows: list[dict], target_contract: dict, dataset_root: str):
    platform = target_contract["platform"].lower()
    if platform in {"file", "adls", "onelake"}:
        from framework.targets.file_writer import FileWriter

        return FileWriter(dataset_root).write(rows, target_contract)
    if platform in {"delta", "lakehouse", "databricks"}:
        from framework.targets.delta_writer import DeltaWriter

        return DeltaWriter(dataset_root).write(rows, target_contract)
    raise ValueError(f"Unsupported MVP target platform: {platform}")
