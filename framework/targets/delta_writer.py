"""Delta target writer."""

from __future__ import annotations

from pathlib import Path

from framework.targets.file_writer import FileWriter


class DeltaWriter(FileWriter):
    """MVP Delta stand-in that writes deterministic files for local SIT."""

    def write(self, data: list[dict], metadata: dict) -> Path:
        local_metadata = {**metadata, "format": "csv"}
        return super().write(data, local_metadata)
