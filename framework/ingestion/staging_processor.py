"""RAW and STAGING processing for source-shaped file datasets."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DatasetContract:
    """Minimal source contract for a file dataset."""

    dataset_id: str
    table_name: str
    primary_key: str
    expected_columns: list[str]
    source_record_pattern: str

    @property
    def is_mutable(self) -> bool:
        return self.source_record_pattern == "mutable_versioned"


def copy_missing_root_csvs(source_root: str | Path, table_names: list[str]) -> list[Path]:
    """Copy required CSVs from old_datasets when the root-level file is missing."""

    root = Path(source_root)
    copied: list[Path] = []
    old_root = root / "old_datasets"
    for table_name in table_names:
        target = root / table_name
        source = old_root / table_name
        if not target.exists() and source.exists():
            shutil.copy2(source, target)
            copied.append(target)
    return copied


def load_source_metadata(source_root: str | Path) -> dict[str, Any]:
    metadata_path = Path(source_root) / "metadata.json"
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def load_contracts(source_root: str | Path, table_config: dict[str, dict[str, str]]) -> list[DatasetContract]:
    source_metadata = load_source_metadata(source_root)
    contracts: list[DatasetContract] = []
    for table_name, config in table_config.items():
        table_metadata = source_metadata["tables"].get(table_name)
        if table_metadata is None:
            continue
        contracts.append(
            DatasetContract(
                dataset_id=config["dataset_id"],
                table_name=table_name,
                primary_key=config["primary_key"],
                expected_columns=table_metadata["columns"],
                source_record_pattern=config["source_record_pattern"],
            )
        )
    return contracts


def process_dataset_to_staging(
    *,
    source_root: str | Path,
    output_root: str | Path,
    contract: DatasetContract,
    run_id: str,
    batch_date: str,
    source_system_id: str,
    load_type: str = "full",
    source_date: str | None = None,
    ingest_timestamp: str | None = None,
) -> dict[str, Any]:
    """Copy a source file to RAW and write a version-aware STAGING CSV."""

    source_root = Path(source_root)
    output_root = Path(output_root)
    active_ingest_timestamp = ingest_timestamp or datetime.now(UTC).isoformat()
    source_files = _source_files_for_table(source_root, contract.table_name, load_type=load_type, source_date=source_date)
    if not source_files:
        raise FileNotFoundError(f"No source CSV found for {contract.table_name} in {source_root}")

    raw_paths = [
        _copy_to_raw(
            source_file=source_file,
            output_root=output_root,
            table_name=contract.table_name,
            run_id=run_id,
            ingest_timestamp=active_ingest_timestamp,
        )
        for source_file in source_files
    ]

    rows: list[dict[str, str]] = []
    for source_file in source_files:
        rows.extend(_read_source_rows(source_file, contract))

    staged_rows = _stage_rows(
        rows=rows,
        contract=contract,
        source_system_id=source_system_id,
        run_id=run_id,
        batch_date=batch_date,
        load_type=load_type,
        source_date=source_date or "",
        ingest_timestamp=active_ingest_timestamp,
    )
    staging_path = _write_staging(output_root, contract.table_name, batch_date, staged_rows)
    rejected_path = _write_rejects(output_root, contract.table_name, run_id, staged_rows)
    duplicate_count = sum(1 for row in staged_rows if row["_is_exact_duplicate"] == "true")
    ambiguous_count = sum(1 for row in staged_rows if row["_latest_resolution_status"] == "ambiguous_same_timestamp")

    return {
        "dataset_id": contract.dataset_id,
        "table_name": contract.table_name,
        "source_record_pattern": contract.source_record_pattern,
        "load_type": load_type,
        "source_date": source_date or "",
        "source_file_count": len(source_files),
        "source_record_count": len(rows),
        "staging_record_count": len(staged_rows),
        "exact_duplicate_count": duplicate_count,
        "ambiguous_latest_count": ambiguous_count,
        "raw_paths": [str(path) for path in raw_paths],
        "staging_path": str(staging_path),
        "rejected_path": str(rejected_path) if rejected_path else "",
        "status": "SUCCESS" if ambiguous_count == 0 else "SUCCESS_WITH_WARNINGS",
    }


def validate_extract_manifest(
    source_root: str | Path,
    source_date: str,
    table_names: list[str],
    *,
    load_type: str,
) -> dict[str, int]:
    """Validate a dated full or delta manifest and return expected row counts by table."""

    extract_dir = "delta_sources" if load_type == "delta" else "full_sources"
    manifest_path = Path(source_root) / extract_dir / source_date / "manifest.csv"
    if not manifest_path.exists():
        raise FileNotFoundError(f"{load_type} manifest does not exist: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    expected: dict[str, int] = {}
    for row in rows:
        table_name = row["table_name"]
        if table_name not in table_names:
            continue
        expected[table_name] = int(row["row_count"])
        if row.get("source_date") != source_date:
            raise ValueError(f"Manifest source_date mismatch for {table_name}: {row.get('source_date')}")

    missing = sorted(set(table_names).difference(expected))
    if missing and load_type == "full":
        raise ValueError(f"Full extract manifest missing tables: {missing}")
    return expected


def validate_delta_manifest(source_root: str | Path, source_date: str, table_names: list[str]) -> dict[str, int]:
    """Validate the delta manifest and return expected row counts by table."""

    return validate_extract_manifest(source_root, source_date, table_names, load_type="delta")


def _source_files_for_table(
    source_root: Path,
    table_name: str,
    *,
    load_type: str,
    source_date: str | None,
) -> list[Path]:
    active_root = source_root
    if load_type == "delta":
        if not source_date:
            raise ValueError("source_date is required for delta loads")
        active_root = source_root / "delta_sources" / source_date
    elif load_type == "full" and source_date:
        active_root = source_root / "full_sources" / source_date
    stem = Path(table_name).stem
    candidates = [
        path
        for path in active_root.glob("*.csv")
        if path.name == table_name or path.name.startswith(f"{stem}_")
    ]
    return sorted(candidates)


def _read_source_rows(source_file: Path, contract: DatasetContract) -> list[dict[str, str]]:
    with source_file.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        actual_columns = reader.fieldnames or []
        expected_columns = contract.expected_columns
        if actual_columns == [*contract.expected_columns, "delta_action"]:
            expected_columns = [*contract.expected_columns, "delta_action"]
        if actual_columns != expected_columns:
            raise ValueError(
                f"{source_file.name} schema mismatch. "
                f"Expected {contract.expected_columns} or delta columns; got {actual_columns}"
            )
        rows = []
        for source_row_number, row in enumerate(reader, start=2):
            if contract.is_mutable and (not row.get("effective_at") or not row.get("updated_at")):
                raise ValueError(f"{source_file.name} row {source_row_number} missing effective_at or updated_at")
            row["_source_file_name"] = source_file.name
            row["_source_file_path"] = str(source_file)
            row["_source_file_modified_at"] = datetime.fromtimestamp(
                source_file.stat().st_mtime,
                UTC,
            ).isoformat()
            row["_source_row_number"] = str(source_row_number)
            rows.append(row)
    return rows


def _stage_rows(
    *,
    rows: list[dict[str, str]],
    contract: DatasetContract,
    source_system_id: str,
    run_id: str,
    batch_date: str,
    load_type: str,
    source_date: str,
    ingest_timestamp: str,
) -> list[dict[str, str]]:
    staged_rows: list[dict[str, str]] = []
    seen_exact: set[tuple[str, str, str, str]] = set()
    for row in rows:
        payload = {column: row.get(column, "") for column in contract.expected_columns}
        delta_action = row.get("delta_action", "UPSERT" if load_type == "full" else "")
        record_hash = _record_hash(payload)
        exact_key = (
            row[contract.primary_key],
            row.get("effective_at", ""),
            row.get("updated_at", ""),
            record_hash,
        )
        staged = {
            **payload,
            "_source_system_id": source_system_id,
            "_source_dataset_id": contract.dataset_id,
            "_source_file_name": row["_source_file_name"],
            "_source_file_path": row["_source_file_path"],
            "_source_file_modified_at": row["_source_file_modified_at"],
            "_source_row_number": row["_source_row_number"],
            "_ingest_run_id": run_id,
            "_ingest_timestamp": ingest_timestamp,
            "_batch_date": batch_date,
            "_load_type": load_type,
            "_source_extract_date": source_date,
            "_delta_action": delta_action,
            "_DQ_STATUS": "passed",
            "_record_hash": record_hash,
            "_is_exact_duplicate": "true" if exact_key in seen_exact else "false",
            "_is_latest_for_business_key": "false",
            "_latest_resolution_status": "pending" if contract.is_mutable else "not_applicable_event",
        }
        seen_exact.add(exact_key)
        staged_rows.append(staged)

    if contract.is_mutable:
        _mark_latest_mutable_rows(staged_rows, contract.primary_key)
    return staged_rows


def _mark_latest_mutable_rows(rows: list[dict[str, str]], primary_key: str) -> None:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row[primary_key], []).append(row)

    for key_rows in grouped.values():
        non_duplicate_rows = [row for row in key_rows if row["_is_exact_duplicate"] == "false"]
        ordered = sorted(
            non_duplicate_rows,
            key=lambda row: (
                row["updated_at"],
                row["effective_at"],
                row["_source_file_modified_at"],
                row["_ingest_timestamp"],
                row["_source_file_name"],
                int(row["_source_row_number"]),
            ),
            reverse=True,
        )
        if not ordered:
            continue
        top = ordered[0]
        same_source_time = [
            row
            for row in ordered
            if row["updated_at"] == top["updated_at"] and row["effective_at"] == top["effective_at"]
        ]
        top_hashes = {row["_record_hash"] for row in same_source_time}
        if len(top_hashes) > 1:
            for row in same_source_time:
                row["_latest_resolution_status"] = "ambiguous_same_timestamp"
            continue
        top["_is_latest_for_business_key"] = "true"
        top["_latest_resolution_status"] = "resolved"
        for row in ordered[1:]:
            if row["_latest_resolution_status"] == "pending":
                row["_latest_resolution_status"] = "resolved"


def _record_hash(payload: dict[str, str]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _copy_to_raw(
    *,
    source_file: Path,
    output_root: Path,
    table_name: str,
    run_id: str,
    ingest_timestamp: str,
) -> Path:
    ingest_dt = datetime.fromisoformat(ingest_timestamp.replace("Z", "+00:00"))
    target = (
        output_root
        / "raw"
        / "source_system=element_fleet_services_synthetic"
        / f"dataset={Path(table_name).stem}"
        / f"source_extract={source_file.parent.name if source_file.parent.name != 'element-fleet-services' else 'root'}"
        / f"ingest_date={ingest_dt.date().isoformat()}"
        / f"ingest_hour={ingest_dt.strftime('%H')}"
        / f"run_id={run_id}"
        / source_file.name
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_file, target)
    return target


def _write_staging(output_root: Path, table_name: str, batch_date: str, rows: list[dict[str, str]]) -> Path:
    target = (
        output_root
        / "staging"
        / "domain=fleet_management"
        / f"dataset={Path(table_name).stem}"
        / f"batch_date={batch_date}"
        / "part-00000.csv"
    )
    _write_csv(target, rows)
    return target


def _write_rejects(output_root: Path, table_name: str, run_id: str, rows: list[dict[str, str]]) -> Path | None:
    rejected = [row for row in rows if row["_latest_resolution_status"] == "ambiguous_same_timestamp"]
    if not rejected:
        return None
    target = (
        output_root
        / "staging_rejects"
        / "domain=fleet_management"
        / f"dataset={Path(table_name).stem}"
        / f"run_id={run_id}"
        / "ambiguous_latest.csv"
    )
    _write_csv(target, rejected)
    return target


def _write_csv(target: Path, rows: list[dict[str, str]]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
