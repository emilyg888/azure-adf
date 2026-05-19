"""Generic ingestion driver for Fabric notebooks and local SIT execution."""

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
from framework.ingestion.landing_validator import LandingValidator
from framework.ingestion.source_reader import SourceReader
from framework.metadata.metadata_reader import MetadataReader
from framework.metadata.metadata_validator import MetadataValidator


def load_environment_config(environment: str) -> dict:
    path = ROOT / "fabric" / "environments" / f"{environment}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def run_ingestion(
    environment: str = "dev",
    dataset_id: str | None = None,
    dataset_group: str | None = None,
    run_mode: str = "manual",
    batch_date: str | None = None,
    full_refresh_flag: bool = False,
    dataset_root: str | Path | None = None,
    metadata_path: str | Path | None = None,
    audit_path: str | Path | None = None,
) -> list[dict]:
    config = load_environment_config(environment)
    resolved_dataset_root = Path(dataset_root or config["bb_dataset_root"]).resolve()
    resolved_metadata_path = Path(metadata_path or ROOT / "metadata/seed/ingestion_metadata.json")
    resolved_audit_path = Path(audit_path or resolved_dataset_root / "audit/phase_1_ingestion_audit.jsonl")

    run_id = f"RUN_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    reader = MetadataReader(resolved_metadata_path)
    validator = MetadataValidator()
    source_reader = SourceReader(resolved_dataset_root)
    landing_validator = LandingValidator(resolved_dataset_root)
    audit = AuditLogger(resolved_audit_path)

    results: list[dict] = []
    for dataset in reader.list_active_datasets(dataset_id=dataset_id, dataset_group=dataset_group):
        started_at = datetime.now(UTC).isoformat()
        source = reader.read_source(dataset["dataset_id"])
        target = reader.read_target(dataset["dataset_id"])
        activity = "CopyData"
        try:
            metadata_errors = validator.validate_ingestion_metadata(dataset, source, target)
            if metadata_errors:
                raise ValueError("; ".join(metadata_errors))

            source_count = source_reader.read_count(source)
            source_reader.copy_to_target(source, target)
            validation = landing_validator.validate_landing(
                run_id=run_id,
                dataset_id=dataset["dataset_id"],
                target=target,
                source_record_count=source_count,
            )
            event = audit.log(
                {
                    "run_id": run_id,
                    "dataset_id": dataset["dataset_id"],
                    "pipeline_name": "pl_metadata_driven_ingestion",
                    "activity_name": activity,
                    "status": "SUCCESS",
                    "source_record_count": source_count,
                    "target_record_count": validation["target_record_count"],
                    "warning_count": len(validation["warnings"]),
                    "run_mode": run_mode,
                    "batch_date": batch_date,
                    "full_refresh_flag": full_refresh_flag,
                    "code_version": "phase_1_mvp",
                    "metadata_version": reader.metadata_version(),
                    "started_at": started_at,
                    "completed_at": datetime.now(UTC).isoformat(),
                }
            )
        except Exception as exc:
            event = audit.log(
                {
                    "run_id": run_id,
                    "dataset_id": dataset["dataset_id"],
                    "pipeline_name": "pl_metadata_driven_ingestion",
                    "activity_name": activity,
                    "status": "FAILED",
                    "source_record_count": 0,
                    "target_record_count": 0,
                    "error_message": str(exc),
                    "run_mode": run_mode,
                    "batch_date": batch_date,
                    "full_refresh_flag": full_refresh_flag,
                    "code_version": "phase_1_mvp",
                    "metadata_version": reader.metadata_version(),
                    "started_at": started_at,
                    "completed_at": datetime.now(UTC).isoformat(),
                }
            )
        results.append(event)
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", default="dev")
    parser.add_argument("--dataset-id", default=None)
    parser.add_argument("--dataset-group", default=None)
    parser.add_argument("--run-mode", default="manual")
    parser.add_argument("--batch-date", default=None)
    parser.add_argument("--full-refresh-flag", action="store_true")
    parser.add_argument("--dataset-root", default=None)
    parser.add_argument("--metadata-path", default=None)
    parser.add_argument("--audit-path", default=None)
    args = parser.parse_args()
    results = run_ingestion(
        environment=args.environment,
        dataset_id=args.dataset_id,
        dataset_group=args.dataset_group,
        run_mode=args.run_mode,
        batch_date=args.batch_date,
        full_refresh_flag=args.full_refresh_flag,
        dataset_root=args.dataset_root,
        metadata_path=args.metadata_path,
        audit_path=args.audit_path,
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
