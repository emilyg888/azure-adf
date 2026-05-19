from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_phase_0_contract_templates_exist():
    assert (ROOT / "metadata/contracts/dataset_contract_template.yaml").is_file()
    assert (ROOT / "metadata/contracts/transformation_contract_template.yaml").is_file()


def test_phase_0_core_docs_exist():
    expected = [
        "docs/architecture.md",
        "docs/metadata_model.md",
        "docs/operating_model.md",
        "docs/onboarding_new_dataset.md",
        "docs/governance_design.md",
        "docs/release_process.md",
        "docs/package_boundaries.md",
        "design/decisions/ADR-0001-framework-principles.md",
    ]
    for relative_path in expected:
        assert (ROOT / relative_path).is_file(), relative_path


def test_phase_0_environment_configs_are_named():
    for environment in ["dev", "test", "prod"]:
        text = (ROOT / f"fabric/environments/{environment}.json").read_text()
        assert f'"environment": "{environment}"' in text
        assert "metadata_database" in text
