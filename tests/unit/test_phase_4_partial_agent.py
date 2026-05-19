import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_agent_prompt_templates_exist():
    expected = [
        "agent/prompts/generate_transform.md",
        "agent/prompts/generate_tests.md",
        "agent/prompts/generate_mapping_doc.md",
        "agent/prompts/review_generated_code.md",
    ]
    for relative_path in expected:
        assert (ROOT / relative_path).is_file(), relative_path


def test_agent_task_and_generated_assets_registered():
    metadata = json.loads((ROOT / "metadata/seed/agent_task_metadata.json").read_text(encoding="utf-8"))
    assert metadata["agent_tasks"][0]["agent_task_id"] == "AGT_POP_001"
    asset_paths = {asset["repo_path"] for asset in metadata["generated_code_assets"]}
    assert "transforms/pyspark/population_by_age_transform.py" in asset_paths
    assert "tests/unit/test_population_by_age_transform.py" in asset_paths
    assert "docs/mappings/population_by_age_mapping.md" in asset_paths
    assert all(asset["active_flag"] is False for asset in metadata["generated_code_assets"])


def test_generated_review_artefacts_exist():
    assert (ROOT / "agent/review_checklists/generated_transform_review.md").is_file()
    assert (ROOT / "agent/generated_assets/AGT_POP_001/review_summary.md").is_file()
    assert (ROOT / "docs/mappings/population_by_age_mapping.md").is_file()


def test_runtime_code_has_no_llm_dependency():
    runtime_files = [
        ROOT / "transforms/pyspark/population_by_age_transform.py",
        ROOT / "fabric/notebooks/generic_transform_driver.py",
    ]
    forbidden = ["openai", "llm", "chatcompletion", "responses.create"]
    for path in runtime_files:
        text = path.read_text(encoding="utf-8").lower()
        assert not any(token in text for token in forbidden), path
