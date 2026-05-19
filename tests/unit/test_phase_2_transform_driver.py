import csv
from pathlib import Path

from fabric.notebooks.generic_transform_driver import run_transform


ROOT = Path(__file__).resolve().parents[2]


def copy_fixture(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def test_phase_2_sit_transforms_and_writes_output(tmp_path):
    dataset_root = tmp_path / "bb_datasets/phase_2"
    fixture_root = ROOT / "tests/fixtures/bb_datasets/phase_2"
    copy_fixture(
        fixture_root / "raw/population/population_by_age.tsv",
        dataset_root / "raw/population/population_by_age.tsv",
    )
    copy_fixture(fixture_root / "lookup/dim_country.csv", dataset_root / "lookup/dim_country.csv")

    result = run_transform(dataset_root=dataset_root)

    assert result["status"] == "SUCCESS"
    assert result["input_record_count"] == 13
    assert result["output_record_count"] == 2
    output_path = dataset_root / "processed/population_by_age/population_by_age.csv"
    assert output_path.is_file()
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["country"] == "Australia"
    assert rows[0]["age_group_0_14"] == "18.7"
