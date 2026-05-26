import csv
import json
from pathlib import Path

from fabric.notebooks.element_fleet_pipeline_driver import run_element_fleet_pipeline
from framework.conformed.scd_processor import merge_scd2_dimension
from framework.ingestion.staging_processor import DatasetContract, process_dataset_to_staging


def test_staging_marks_latest_mutable_record(tmp_path):
    source_root = tmp_path / "source"
    output_root = tmp_path / "out"
    source_root.mkdir()
    _write_csv(
        source_root / "leasing_contracts.csv",
        [
            {
                "lease_id": "L1",
                "lease_status": "Active",
                "effective_at": "2026-05-26T09:00:00",
                "updated_at": "2026-05-26T09:15:00",
            },
            {
                "lease_id": "L1",
                "lease_status": "Closed",
                "effective_at": "2026-05-26T11:00:00",
                "updated_at": "2026-05-26T11:05:00",
            },
        ],
    )
    contract = DatasetContract(
        dataset_id="DS_FLEET_LEASING_CONTRACTS_001",
        table_name="leasing_contracts.csv",
        primary_key="lease_id",
        expected_columns=["lease_id", "lease_status", "effective_at", "updated_at"],
        source_record_pattern="mutable_versioned",
    )

    result = process_dataset_to_staging(
        source_root=source_root,
        output_root=output_root,
        contract=contract,
        run_id="RUN_TEST",
        batch_date="2026-05-26",
        source_system_id="SRC_ELEMENT_FLEET_SYNTH_001",
        ingest_timestamp="2026-05-26T01:00:00+00:00",
    )

    rows = _read_csv(Path(result["staging_path"]))
    assert result["status"] == "SUCCESS"
    assert sum(row["_is_latest_for_business_key"] == "true" for row in rows) == 1
    assert [row for row in rows if row["_is_latest_for_business_key"] == "true"][0]["lease_status"] == "Closed"


def test_staging_quarantines_ambiguous_same_timestamp(tmp_path):
    source_root = tmp_path / "source"
    output_root = tmp_path / "out"
    source_root.mkdir()
    _write_csv(
        source_root / "clients.csv",
        [
            {
                "client_id": "C1",
                "client_status": "Active",
                "effective_at": "2026-05-26T09:00:00",
                "updated_at": "2026-05-26T09:15:00",
            },
            {
                "client_id": "C1",
                "client_status": "Suspended",
                "effective_at": "2026-05-26T09:00:00",
                "updated_at": "2026-05-26T09:15:00",
            },
        ],
    )
    contract = DatasetContract(
        dataset_id="DS_FLEET_CLIENTS_001",
        table_name="clients.csv",
        primary_key="client_id",
        expected_columns=["client_id", "client_status", "effective_at", "updated_at"],
        source_record_pattern="mutable_versioned",
    )

    result = process_dataset_to_staging(
        source_root=source_root,
        output_root=output_root,
        contract=contract,
        run_id="RUN_TEST",
        batch_date="2026-05-26",
        source_system_id="SRC_ELEMENT_FLEET_SYNTH_001",
        ingest_timestamp="2026-05-26T01:00:00+00:00",
    )

    rows = _read_csv(Path(result["staging_path"]))
    assert result["status"] == "SUCCESS_WITH_WARNINGS"
    assert result["ambiguous_latest_count"] == 2
    assert all(row["_latest_resolution_status"] == "ambiguous_same_timestamp" for row in rows)
    assert Path(result["rejected_path"]).is_file()


def test_element_fleet_pipeline_uses_current_root_schema(tmp_path):
    source_root = tmp_path / "source"
    output_root = tmp_path / "out"
    source_root.mkdir()
    metadata = {
        "tables": {
            "clients.csv": {
                "columns": [
                    "client_id",
                    "client_name",
                    "industry_segment",
                    "headquarters_state",
                    "fleet_size_band",
                    "contract_start_date",
                    "client_status",
                    "effective_at",
                    "updated_at",
                ]
            }
        }
    }
    (source_root / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    _write_csv(
        source_root / "clients.csv",
        [
            {
                "client_id": "C1",
                "client_name": "Client One",
                "industry_segment": "Health",
                "headquarters_state": "NSW",
                "fleet_size_band": "1-50",
                "contract_start_date": "2024-01-01",
                "client_status": "Active",
                "effective_at": "2026-05-26T09:00:00",
                "updated_at": "2026-05-26T09:15:00",
            }
        ],
    )

    result = run_element_fleet_pipeline(
        source_root=source_root,
        output_root=output_root,
        dataset_id="DS_FLEET_CLIENTS_001",
        batch_date="2026-05-26",
        run_id="RUN_TEST",
    )[0]

    assert result["status"] == "SUCCESS"
    assert result["source_record_count"] == 1
    assert Path(result["staging_path"]).is_file()


def test_element_fleet_pipeline_processes_manifest_delta(tmp_path):
    source_root = tmp_path / "source"
    delta_root = source_root / "delta_sources" / "2026-05-26"
    output_root = tmp_path / "out"
    delta_root.mkdir(parents=True)
    metadata = {
        "tables": {
            "clients.csv": {
                "columns": [
                    "client_id",
                    "client_name",
                    "industry_segment",
                    "headquarters_state",
                    "fleet_size_band",
                    "contract_start_date",
                    "client_status",
                    "effective_at",
                    "updated_at",
                ]
            }
        }
    }
    (source_root / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    _write_csv(
        delta_root / "manifest.csv",
        [
            {
                "source_date": "2026-05-26",
                "table_name": "clients.csv",
                "row_count": "1",
                "delta_type": "synthetic_update_extract",
            }
        ],
    )
    _write_csv(
        delta_root / "clients.csv",
        [
            {
                "client_id": "C1",
                "client_name": "Client One",
                "industry_segment": "Health",
                "headquarters_state": "NSW",
                "fleet_size_band": "1-50",
                "contract_start_date": "2024-01-01",
                "client_status": "Active",
                "effective_at": "2026-05-26T09:00:00",
                "updated_at": "2026-05-26T09:15:00",
                "delta_action": "UPDATE",
            }
        ],
    )

    result = run_element_fleet_pipeline(
        source_root=source_root,
        output_root=output_root,
        dataset_id="DS_FLEET_CLIENTS_001",
        load_type="delta",
        source_date="2026-05-26",
        batch_date="2026-05-26",
        run_id="RUN_TEST",
    )[0]
    rows = _read_csv(Path(result["staging_path"]))

    assert result["status"] == "SUCCESS"
    assert result["load_type"] == "delta"
    assert result["source_date"] == "2026-05-26"
    assert rows[0]["_delta_action"] == "UPDATE"
    assert rows[0]["_source_extract_date"] == "2026-05-26"


def test_two_full_extract_days_drive_scd2_changes_and_soft_delete(tmp_path):
    source_root = tmp_path / "source"
    output_root = tmp_path / "out"
    day1 = source_root / "full_sources" / "2026-05-25"
    day2 = source_root / "full_sources" / "2026-05-26"
    day1.mkdir(parents=True)
    day2.mkdir(parents=True)
    metadata = {
        "tables": {
            "clients.csv": {
                "columns": [
                    "client_id",
                    "client_name",
                    "industry_segment",
                    "headquarters_state",
                    "fleet_size_band",
                    "contract_start_date",
                    "client_status",
                    "effective_at",
                    "updated_at",
                ]
            }
        }
    }
    (source_root / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    _write_manifest(day1 / "manifest.csv", "2026-05-25", "clients.csv", "2")
    _write_manifest(day2 / "manifest.csv", "2026-05-26", "clients.csv", "1")
    _write_csv(
        day1 / "clients.csv",
        [
            _client_row("C1", "Active", "2026-05-25T09:00:00", "2026-05-25T09:05:00"),
            _client_row("C2", "Active", "2026-05-25T09:00:00", "2026-05-25T09:05:00"),
        ],
    )
    _write_csv(
        day2 / "clients.csv",
        [
            _client_row("C1", "Suspended", "2026-05-26T09:00:00", "2026-05-26T09:05:00"),
        ],
    )

    day1_result = run_element_fleet_pipeline(
        source_root=source_root,
        output_root=output_root,
        dataset_id="DS_FLEET_CLIENTS_001",
        load_type="full",
        source_date="2026-05-25",
        batch_date="2026-05-25",
        run_id="RUN_DAY1",
    )[0]
    day2_result = run_element_fleet_pipeline(
        source_root=source_root,
        output_root=output_root,
        dataset_id="DS_FLEET_CLIENTS_001",
        load_type="full",
        source_date="2026-05-26",
        batch_date="2026-05-26",
        run_id="RUN_DAY2",
    )[0]

    conformed = merge_scd2_dimension(
        current_rows=[],
        staging_rows=_read_csv(Path(day1_result["staging_path"])),
        business_key="client_id",
        surrogate_key="client_sk",
        run_id="RUN_DAY1",
        batch_timestamp="2026-05-25T12:00:00",
    )
    conformed = merge_scd2_dimension(
        current_rows=conformed,
        staging_rows=_read_csv(Path(day2_result["staging_path"])),
        business_key="client_id",
        surrogate_key="client_sk",
        run_id="RUN_DAY2",
        batch_timestamp="2026-05-26T12:00:00",
    )

    c1_rows = [row for row in conformed if row["client_id"] == "C1"]
    c2_rows = [row for row in conformed if row["client_id"] == "C2"]
    assert len(c1_rows) == 2
    assert [row for row in c1_rows if row["is_current"] == "true"][0]["client_status"] == "Suspended"
    assert c2_rows[0]["is_current"] == "false"
    assert c2_rows[0]["deleted_flag"] == "true"
    assert c2_rows[0]["effective_to"] == "2026-05-26T12:00:00"


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_manifest(path: Path, source_date: str, table_name: str, row_count: str) -> None:
    _write_csv(
        path,
        [
            {
                "source_date": source_date,
                "table_name": table_name,
                "row_count": row_count,
                "extract_type": "synthetic_full_daily_extract",
                "changed_from_previous_extract": "Y",
            }
        ],
    )


def _client_row(client_id: str, status: str, effective_at: str, updated_at: str) -> dict[str, str]:
    return {
        "client_id": client_id,
        "client_name": f"Client {client_id}",
        "industry_segment": "Health",
        "headquarters_state": "NSW",
        "fleet_size_band": "1-50",
        "contract_start_date": "2024-01-01",
        "client_status": status,
        "effective_at": effective_at,
        "updated_at": updated_at,
    }
