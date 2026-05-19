"""Lightweight Erwin export ingestion for Phase 1A."""

from __future__ import annotations

import csv
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REQUIRED_FILES = {
    "erwin_model.csv": ["model_name", "model_version", "subject_area", "export_timestamp", "exported_by"],
    "erwin_objects.csv": [
        "model_name",
        "model_version",
        "subject_area",
        "logical_entity_name",
        "physical_object_name",
        "object_type",
        "platform_hint",
        "description",
    ],
    "erwin_columns.csv": [
        "model_name",
        "model_version",
        "physical_object_name",
        "logical_attribute_name",
        "physical_column_name",
        "data_type",
        "length",
        "precision",
        "scale",
        "nullable_flag",
        "primary_key_flag",
        "business_definition",
        "domain_name",
        "classification",
    ],
    "erwin_mappings.csv": [
        "model_name",
        "model_version",
        "source_system_name",
        "source_object_name",
        "source_column_name",
        "target_system_name",
        "target_object_name",
        "target_column_name",
        "transformation_text",
        "business_definition",
        "classification",
    ],
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_export(export_path: str | Path) -> list[str]:
    path = Path(export_path)
    errors: list[str] = []
    for file_name, required_columns in REQUIRED_FILES.items():
        file_path = path / file_name
        if not file_path.exists():
            errors.append(f"{file_name} is required")
            continue
        with file_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames or []
            missing = [column for column in required_columns if column not in columns]
            errors.extend(f"{file_name}.{column} is required" for column in missing)

    model_rows = read_csv(path / "erwin_model.csv") if (path / "erwin_model.csv").exists() else []
    for row_number, row in enumerate(model_rows, start=2):
        if not row.get("model_name"):
            errors.append(f"erwin_model.csv:{row_number} model_name is required")
        if not row.get("model_version"):
            errors.append(f"erwin_model.csv:{row_number} model_version is required")

    column_rows = read_csv(path / "erwin_columns.csv") if (path / "erwin_columns.csv").exists() else []
    seen_columns: set[tuple[str, str]] = set()
    for row_number, row in enumerate(column_rows, start=2):
        key = (row.get("physical_object_name", ""), row.get("physical_column_name", ""))
        if not key[0]:
            errors.append(f"erwin_columns.csv:{row_number} physical_object_name is required")
        if not key[1]:
            errors.append(f"erwin_columns.csv:{row_number} physical_column_name is required")
        if key in seen_columns:
            errors.append(f"erwin_columns.csv:{row_number} duplicate physical object + column: {key}")
        seen_columns.add(key)
    return errors


def ingest_erwin_export(export_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    """Load one strict Erwin export into JSON staging evidence."""
    source_path = Path(export_path)
    target_path = Path(output_path)
    target_path.mkdir(parents=True, exist_ok=True)

    errors = validate_export(source_path)
    model_rows = read_csv(source_path / "erwin_model.csv") if not errors else []
    model = model_rows[0] if model_rows else {}
    model_version_id = f"MDL_{uuid.uuid4().hex[:12]}"
    imported_at = datetime.now(UTC).isoformat()
    status = "FAILED" if errors else "SUCCESS"

    staged: dict[str, Any] = {
        "model_version": {
            "model_version_id": model_version_id,
            "model_name": model.get("model_name", ""),
            "erwin_model_version": model.get("model_version", ""),
            "export_timestamp": model.get("export_timestamp", ""),
            "export_source": str(source_path),
            "imported_by": model.get("exported_by", ""),
            "import_status": status,
            "active_flag": status == "SUCCESS",
        },
        "stg_erwin_model": [],
        "stg_erwin_object": [],
        "stg_erwin_column": [],
        "stg_erwin_mapping": [],
        "errors": errors,
    }

    if not errors:
        staged["stg_erwin_model"] = [
            {
                "model_version_id": model_version_id,
                "model_name": row["model_name"],
                "erwin_model_version": row["model_version"],
                "subject_area": row["subject_area"],
                "export_timestamp": row["export_timestamp"],
                "exported_by": row["exported_by"],
                "import_status": status,
                "imported_at": imported_at,
            }
            for row in read_csv(source_path / "erwin_model.csv")
        ]
        staged["stg_erwin_object"] = [
            {"model_version_id": model_version_id, "erwin_model_version": row.pop("model_version"), **row}
            for row in read_csv(source_path / "erwin_objects.csv")
        ]
        staged["stg_erwin_column"] = [
            {"model_version_id": model_version_id, "erwin_model_version": row.pop("model_version"), **row}
            for row in read_csv(source_path / "erwin_columns.csv")
        ]
        staged["stg_erwin_mapping"] = [
            {"model_version_id": model_version_id, "erwin_model_version": row.pop("model_version"), **row}
            for row in read_csv(source_path / "erwin_mappings.csv")
        ]

    report = {
        "model_name": staged["model_version"]["model_name"],
        "model_version": staged["model_version"]["erwin_model_version"],
        "export_timestamp": staged["model_version"]["export_timestamp"],
        "object_count": len(staged["stg_erwin_object"]),
        "column_count": len(staged["stg_erwin_column"]),
        "mapping_count": len(staged["stg_erwin_mapping"]),
        "rejected_row_count": len(errors),
        "warning_count": 0,
        "import_status": status,
        "errors": errors,
    }
    (target_path / "erwin_staging.json").write_text(json.dumps(staged, indent=2), encoding="utf-8")
    (target_path / "erwin_ingestion_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
