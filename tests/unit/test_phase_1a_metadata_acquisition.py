from pathlib import Path

from erwin.model_ingestion.erwin_loader import ingest_erwin_export, validate_export
from erwin.model_ingestion.platform_discovery import discover_file


ROOT = Path(__file__).resolve().parents[2]


def test_valid_erwin_export_loads_to_staging(tmp_path):
    export_path = ROOT / "tests/fixtures/bb_datasets/phase_1a/erwin/exports/reference_data_model/v0_1"
    report = ingest_erwin_export(export_path, tmp_path)

    assert report["import_status"] == "SUCCESS"
    assert report["object_count"] == 1
    assert report["column_count"] == 2
    assert report["mapping_count"] == 3
    assert (tmp_path / "erwin_staging.json").is_file()
    assert (tmp_path / "erwin_ingestion_report.json").is_file()


def test_erwin_export_missing_model_version_fails(tmp_path):
    export_path = tmp_path / "export"
    export_path.mkdir()
    fixture = ROOT / "tests/fixtures/bb_datasets/phase_1a/erwin/exports/reference_data_model/v0_1"
    for source in fixture.glob("*.csv"):
        content = source.read_text(encoding="utf-8")
        if source.name == "erwin_model.csv":
            content = content.replace("reference_data_model,v0_1", "reference_data_model,")
        (export_path / source.name).write_text(content, encoding="utf-8")

    errors = validate_export(export_path)
    assert any("model_version is required" in error for error in errors)


def test_platform_discovery_profiles_population_source(tmp_path):
    dataset_root = tmp_path / "phase_1a"
    source = dataset_root / "raw/population"
    source.mkdir(parents=True)
    fixture = ROOT / "tests/fixtures/bb_datasets/phase_1/raw/population/population_by_age.tsv"
    (source / "population_by_age.tsv").write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    result = discover_file(
        dataset_root=dataset_root,
        dataset_id="DS_REF_POPULATION_001",
        relative_path="/raw/population/population_by_age.tsv",
        output_path=tmp_path / "discovery",
    )

    assert result["report"]["discovery_status"] == "SUCCESS"
    assert result["report"]["column_count"] == 2
    assert result["disc_file_profile"][0]["sample_row_count"] == 12
    assert (tmp_path / "discovery/platform_discovery_report.json").is_file()
