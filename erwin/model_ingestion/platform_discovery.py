"""Local platform metadata discovery for Phase 1A."""

from __future__ import annotations

import csv
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.ingestion.source_reader import DELIMITERS


def infer_type(value: str) -> str:
    if value == "":
        return "string"
    try:
        int(value)
        return "integer"
    except ValueError:
        pass
    try:
        float(value)
        return "decimal"
    except ValueError:
        return "string"


def discover_file(
    dataset_root: str | Path,
    dataset_id: str,
    relative_path: str,
    file_format: str = "csv",
    delimiter: str = "tab",
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Profile one local file as a stand-in for ADLS/OneLake file discovery."""
    root = Path(dataset_root)
    file_path = root / relative_path.lstrip("/")
    discovery_run_id = f"DISC_{uuid.uuid4().hex[:12]}"
    discovered_at = datetime.now(UTC).isoformat()
    if not file_path.exists():
        raise FileNotFoundError(f"Discovery path does not exist: {file_path}")

    csv_delimiter = DELIMITERS.get(delimiter, ",")
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=csv_delimiter))
    headers = list(rows[0].keys()) if rows else []
    sample = rows[0] if rows else {}

    object_row = {
        "discovery_run_id": discovery_run_id,
        "platform_name": "ADLS",
        "database_name": "",
        "schema_name": "",
        "object_name": file_path.name,
        "object_type": "file",
        "object_path": relative_path,
        "file_format": file_format,
        "discovered_at": discovered_at,
    }
    column_rows = [
        {
            "discovery_run_id": discovery_run_id,
            "platform_name": "ADLS",
            "database_name": "",
            "schema_name": "",
            "object_name": file_path.name,
            "column_name": column,
            "data_type": infer_type(sample.get(column, "")),
            "nullable_flag": True,
            "ordinal_position": index,
            "sample_value": sample.get(column, ""),
            "discovered_at": discovered_at,
        }
        for index, column in enumerate(headers, start=1)
    ]
    stat = file_path.stat()
    profile = {
        "discovery_run_id": discovery_run_id,
        "dataset_id": dataset_id,
        "path": relative_path,
        "file_format": file_format,
        "delimiter": delimiter,
        "header_flag": True,
        "file_count": 1,
        "total_size_bytes": stat.st_size,
        "inferred_column_count": len(headers),
        "sample_row_count": len(rows),
        "latest_modified_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
        "discovered_at": discovered_at,
    }
    result = {
        "disc_platform_object": [object_row],
        "disc_platform_column": column_rows,
        "disc_file_profile": [profile],
        "report": {
            "discovery_run_id": discovery_run_id,
            "platform_name": "ADLS",
            "object_count": 1,
            "column_count": len(column_rows),
            "file_count": 1,
            "schema_inferred_flag": bool(headers),
            "discovery_status": "SUCCESS",
            "warning_count": 0 if rows else 1,
        },
    }

    if output_path:
        target = Path(output_path)
        target.mkdir(parents=True, exist_ok=True)
        (target / "platform_discovery.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (target / "platform_discovery_report.json").write_text(
            json.dumps(result["report"], indent=2),
            encoding="utf-8",
        )
    return result
