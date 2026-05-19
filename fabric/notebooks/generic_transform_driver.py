"""Generic transformation driver for Fabric notebooks and local SIT execution."""

from __future__ import annotations

import argparse
import csv
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.audit.audit_logger import AuditLogger
from framework.ingestion.source_reader import DELIMITERS
from framework.metadata.contract_loader import ContractLoader
from framework.targets.target_writer import write_target
from framework.transforms.transform_registry import TransformRegistry


def read_rows(dataset_root: Path, item: dict) -> list[dict]:
    delimiter = DELIMITERS.get(item.get("delimiter", "comma"), ",")
    path = dataset_root / item["path"].lstrip("/")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def validate_output_schema(rows: list[dict], expected_columns: list[str]) -> None:
    if not rows:
        raise ValueError("Transformation output is empty")
    missing = set(expected_columns).difference(rows[0].keys())
    if missing:
        raise ValueError(f"Transformation output missing columns: {sorted(missing)}")


def run_transform(
    environment: str = "dev",
    dataset_id: str = "DS_REF_POPULATION_001",
    run_id: str | None = None,
    contract_path: str | Path | None = None,
    batch_date: str | None = None,
    dataset_root: str | Path | None = None,
    audit_path: str | Path | None = None,
) -> dict:
    resolved_dataset_root = Path(dataset_root or ROOT.parent / "bb_datasets/phase_2").resolve()
    resolved_contract_path = Path(contract_path or ROOT / "metadata/contracts/population_by_age_contract.json")
    resolved_audit_path = Path(audit_path or resolved_dataset_root / "audit/phase_2_transform_audit.jsonl")
    contract = ContractLoader().load(resolved_contract_path)
    if contract["dataset_id"] != dataset_id:
        raise ValueError(f"Contract dataset id {contract['dataset_id']} does not match {dataset_id}")

    transform = TransformRegistry().get(dataset_id)
    started_at = datetime.now(UTC).isoformat()
    active_run_id = run_id or f"RUN_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    audit = AuditLogger(resolved_audit_path)
    try:
        population_rows = read_rows(resolved_dataset_root, contract["inputs"][0])
        country_rows = read_rows(resolved_dataset_root, contract["lookups"][0])
        output_rows = transform(population_rows, country_rows)
        validate_output_schema(output_rows, contract["expected_columns"])
        output_path = write_target(output_rows, contract["target"], str(resolved_dataset_root))
        event = audit.log(
            {
                "run_id": active_run_id,
                "dataset_id": dataset_id,
                "pipeline_name": "pl_generic_transform_driver",
                "activity_name": "TransformAndWrite",
                "status": "SUCCESS",
                "input_record_count": len(population_rows),
                "output_record_count": len(output_rows),
                "target_path": str(output_path),
                "environment": environment,
                "batch_date": batch_date,
                "code_version": "phase_2_mvp",
                "contract_version": contract["contract_version"],
                "started_at": started_at,
                "completed_at": datetime.now(UTC).isoformat(),
            }
        )
    except Exception as exc:
        event = audit.log(
            {
                "run_id": active_run_id,
                "dataset_id": dataset_id,
                "pipeline_name": "pl_generic_transform_driver",
                "activity_name": "TransformAndWrite",
                "status": "FAILED",
                "input_record_count": 0,
                "output_record_count": 0,
                "error_message": str(exc),
                "environment": environment,
                "batch_date": batch_date,
                "code_version": "phase_2_mvp",
                "contract_version": contract.get("contract_version"),
                "started_at": started_at,
                "completed_at": datetime.now(UTC).isoformat(),
            }
        )
    return event


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", default="dev")
    parser.add_argument("--dataset-id", default="DS_REF_POPULATION_001")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--contract-path", default=None)
    parser.add_argument("--batch-date", default=None)
    parser.add_argument("--dataset-root", default=None)
    parser.add_argument("--audit-path", default=None)
    args = parser.parse_args()
    result = run_transform(
        environment=args.environment,
        dataset_id=args.dataset_id,
        run_id=args.run_id,
        contract_path=args.contract_path,
        batch_date=args.batch_date,
        dataset_root=args.dataset_root,
        audit_path=args.audit_path,
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
