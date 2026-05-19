from pathlib import Path

from fabric.notebooks.generic_ingestion_driver import run_ingestion
from framework.audit.audit_logger import read_audit_events
from framework.ingestion.landing_validator import LandingValidator
from framework.metadata.metadata_reader import MetadataReader
from framework.metadata.metadata_validator import MetadataValidator


ROOT = Path(__file__).resolve().parents[2]


def test_metadata_reader_returns_active_population_dataset():
    reader = MetadataReader(ROOT / "metadata/seed/ingestion_metadata.json")
    datasets = reader.list_active_datasets(dataset_id="DS_REF_POPULATION_001")
    assert len(datasets) == 1
    assert datasets[0]["dataset_name"] == "population_by_age"


def test_metadata_validator_catches_missing_source_path():
    reader = MetadataReader(ROOT / "metadata/seed/ingestion_metadata.json")
    dataset = reader.read_dataset("DS_REF_POPULATION_001")
    source = {**reader.read_source("DS_REF_POPULATION_001"), "source_path": ""}
    target = reader.read_target("DS_REF_POPULATION_001")
    errors = MetadataValidator().validate_ingestion_metadata(dataset, source, target)
    assert "source.source_path is required" in errors


def test_landing_validator_reports_missing_target(tmp_path):
    validator = LandingValidator(tmp_path)
    errors = validator.validate("/landing/missing.csv")
    assert errors


def test_phase_1_sit_ingests_population_file(tmp_path):
    fixture_root = ROOT / "tests/fixtures/bb_datasets/phase_1"
    dataset_root = tmp_path / "bb_datasets" / "phase_1"
    source = dataset_root / "raw/population"
    source.mkdir(parents=True)
    (source / "population_by_age.tsv").write_text(
        (fixture_root / "raw/population/population_by_age.tsv").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    audit_path = dataset_root / "audit/phase_1_ingestion_audit.jsonl"

    results = run_ingestion(
        dataset_id="DS_REF_POPULATION_001",
        dataset_root=dataset_root,
        audit_path=audit_path,
    )

    assert results[0]["status"] == "SUCCESS"
    assert results[0]["source_record_count"] == 12
    assert (dataset_root / "landing/reference/population_by_age/population_by_age.tsv").is_file()
    assert read_audit_events(audit_path)[0]["target_record_count"] == 12
