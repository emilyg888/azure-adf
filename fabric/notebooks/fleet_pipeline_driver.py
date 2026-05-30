"""Fleet Services RAW and STAGING pipeline driver."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.audit.audit_logger import AuditLogger
from framework.ingestion.staging_processor import (
    copy_missing_root_csvs,
    load_contracts,
    process_dataset_to_staging,
    validate_extract_manifest,
)


SOURCE_ROOT = Path("/Users/emilygao/LocalDocuments/Projects/bb_datasets/fleet-services")
DEFAULT_OUTPUT_ROOT = ROOT / ".local" / "fleet_pipeline"
DEFAULT_PIPELINE_METADATA_PATH = ROOT / "metadata" / "seed" / "fleet_pipeline_metadata.json"


def run_fleet_pipeline(
    *,
    source_root: str | Path = SOURCE_ROOT,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    pipeline_metadata_path: str | Path = DEFAULT_PIPELINE_METADATA_PATH,
    load_type: str = "full",
    source_date: str | None = None,
    dataset_id: str | None = None,
    dataset_group: str | None = None,
    batch_date: str | None = None,
    run_id: str | None = None,
    audit_path: str | Path | None = None,
) -> list[dict]:
    """Run the local Fleet RAW and STAGING pipeline."""

    resolved_source_root = Path(source_root)
    resolved_output_root = Path(output_root)
    pipeline_metadata = _load_pipeline_metadata(pipeline_metadata_path)
    table_config = pipeline_metadata["table_config"]
    source_system_id = pipeline_metadata["source_system_id"]
    active_batch_date = batch_date or datetime.now(UTC).date().isoformat()
    active_run_id = run_id or f"RUN_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    resolved_audit_path = Path(audit_path or resolved_output_root / "audit" / "fleet_pipeline_audit.jsonl")
    audit = AuditLogger(resolved_audit_path)

    if load_type not in {"full", "delta"}:
        raise ValueError(f"Unsupported load_type: {load_type}")
    if load_type == "full" and not source_date:
        copy_missing_root_csvs(resolved_source_root, list(table_config))
    contracts = load_contracts(resolved_source_root, table_config)
    if load_type == "delta":
        manifest_counts = validate_extract_manifest(
            resolved_source_root,
            source_date or "",
            [contract.table_name for contract in contracts],
            load_type=load_type,
        )
        contracts = [contract for contract in contracts if contract.table_name in manifest_counts]
    elif load_type == "full" and source_date:
        manifest_counts = validate_extract_manifest(
            resolved_source_root,
            source_date,
            [contract.table_name for contract in contracts],
            load_type=load_type,
        )
    else:
        manifest_counts = {}
    if dataset_id:
        contracts = [contract for contract in contracts if contract.dataset_id == dataset_id]
    if dataset_group:
        contracts = [contract for contract in contracts if _dataset_group(contract.table_name) == dataset_group]

    results: list[dict] = []
    for contract in contracts:
        started_at = datetime.now(UTC).isoformat()
        try:
            result = process_dataset_to_staging(
                source_root=resolved_source_root,
                output_root=resolved_output_root,
                contract=contract,
                run_id=active_run_id,
                batch_date=active_batch_date,
                source_system_id=source_system_id,
                load_type=load_type,
                source_date=source_date,
            )
            expected_manifest_count = manifest_counts.get(contract.table_name)
            if expected_manifest_count is not None and result["source_record_count"] != expected_manifest_count:
                raise ValueError(
                    f"Manifest row count mismatch for {contract.table_name}: "
                    f"expected {expected_manifest_count}, got {result['source_record_count']}"
                )
            event = audit.log(
                {
                    **result,
                    "run_id": active_run_id,
                    "pipeline_name": "pl_fleet_raw_to_staging",
                    "activity_name": "RawAndStage",
                    "batch_date": active_batch_date,
                    "load_type": load_type,
                    "source_date": source_date or "",
                    "started_at": started_at,
                    "completed_at": datetime.now(UTC).isoformat(),
                }
            )
        except Exception as exc:
            event = audit.log(
                {
                    "run_id": active_run_id,
                    "dataset_id": contract.dataset_id,
                    "table_name": contract.table_name,
                    "pipeline_name": "pl_fleet_raw_to_staging",
                    "activity_name": "RawAndStage",
                    "status": "FAILED",
                    "error_message": str(exc),
                    "load_type": load_type,
                    "source_date": source_date or "",
                    "source_record_count": 0,
                    "staging_record_count": 0,
                    "batch_date": active_batch_date,
                    "started_at": started_at,
                    "completed_at": datetime.now(UTC).isoformat(),
                }
            )
        results.append(event)
    return results


def _load_pipeline_metadata(pipeline_metadata_path: str | Path) -> dict:
    return json.loads(Path(pipeline_metadata_path).read_text(encoding="utf-8"))


def _dataset_group(table_name: str) -> str:
    if table_name in {"clients.csv", "vehicles.csv"}:
        return "fleet_master_data"
    if table_name in {"fuel_cards.csv", "fuel_card_transactions.csv"}:
        return "fleet_fuel"
    if table_name in {"telematics_daily.csv"}:
        return "fleet_telematics"
    if table_name in {"crm_client_portal_events.csv"}:
        return "fleet_crm"
    if table_name in {"driver_app_events.csv"}:
        return "fleet_driver_app"
    return "fleet_operational"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", default=str(SOURCE_ROOT))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--pipeline-metadata-path", default=str(DEFAULT_PIPELINE_METADATA_PATH))
    parser.add_argument("--load-type", default="full", choices=["full", "delta"])
    parser.add_argument("--source-date", default=None)
    parser.add_argument("--dataset-id", default=None)
    parser.add_argument("--dataset-group", default=None)
    parser.add_argument("--batch-date", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--audit-path", default=None)
    args = parser.parse_args()
    results = run_fleet_pipeline(
        source_root=args.source_root,
        output_root=args.output_root,
        pipeline_metadata_path=args.pipeline_metadata_path,
        load_type=args.load_type,
        source_date=args.source_date,
        dataset_id=args.dataset_id,
        dataset_group=args.dataset_group,
        batch_date=args.batch_date,
        run_id=args.run_id,
        audit_path=args.audit_path,
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
