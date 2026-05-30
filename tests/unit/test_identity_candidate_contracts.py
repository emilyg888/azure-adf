from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_entity_specific_candidate_contracts_exist():
    for relative_path in [
        "metadata/contracts/customer_match_candidate_contract.yaml",
        "metadata/contracts/vehicle_match_candidate_contract.yaml",
        "metadata/contracts/device_vehicle_match_candidate_contract.yaml",
        "metadata/contracts/account_customer_match_candidate_contract.yaml",
    ]:
        assert (ROOT / relative_path).is_file(), relative_path


def test_candidate_contracts_capture_v1_governance_fields():
    for path in (ROOT / "metadata/contracts").glob("*_match_candidate_contract.yaml"):
        text = path.read_text(encoding="utf-8")
        assert "source_table: IDENTITY." in text
        assert "candidate_key: CANDIDATE_ID" in text
        assert "score_table: IDENTITY." in text
        assert "decision_table: IDENTITY." in text
        assert "writeback_staging_table: IDENTITY.STG_" in text
        assert "threshold_policy: IDENTITY.MATCH_THRESHOLD_POLICY" in text
        assert "graph_impact:" in text
        assert "allowed_decision_methods:" in text
        assert "hard_reject_rule" in text
        assert "human_review" in text
        assert "ml_score_band" in text


def test_relationship_contracts_are_marked_as_relationship_confidence_problems():
    for relative_path in [
        "metadata/contracts/device_vehicle_match_candidate_contract.yaml",
        "metadata/contracts/account_customer_match_candidate_contract.yaml",
    ]:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "relationship_confidence_problem: true" in text

