from databricks.notebooks.candidate_match_scoring import ENTITY_CONFIG, recommended_decision, score_candidates


def test_baseline_scorer_covers_v1_identity_entities():
    assert set(ENTITY_CONFIG) == {"CUSTOMER", "VEHICLE", "DEVICE_VEHICLE", "ACCOUNT_CUSTOMER"}
    for config in ENTITY_CONFIG.values():
        assert config["candidate_table"].startswith("IDENTITY.")
        assert config["score_table"].startswith("IDENTITY.STG_")


def test_baseline_scorer_preserves_writeback_contract():
    rows = [
        {
            "CANDIDATE_ID": "C1",
            "ENTITY_TYPE": "CUSTOMER",
            "MATCH_SCORE": 0.97,
            "MATCH_REASON_CODE": "name_address_domain_block",
        }
    ]

    scored = score_candidates(rows, "score_run_1", "mlflow_run_1")

    assert scored == [
        {
            "CANDIDATE_PAIR_ID": "C1",
            "ENTITY_TYPE": "CUSTOMER",
            "MATCH_SCORE": 0.97,
            "RECOMMENDED_DECISION": "MATCH",
            "REASON_CODES": ["name_address_domain_block"],
            "MODEL_NAME": "fleet_identity_candidate_baseline_scorer",
            "MODEL_VERSION": "v0",
            "MLFLOW_RUN_ID": "mlflow_run_1",
            "SCORING_RUN_ID": "score_run_1",
            "FEATURE_SNAPSHOT_ID": "candidate_feature_v1_score_run_1",
            "SCORED_AT": scored[0]["SCORED_AT"],
            "WRITEBACK_BATCH_ID": "score_run_1",
        }
    ]


def test_entity_thresholds_drive_recommended_decision():
    assert recommended_decision("CUSTOMER", 0.96) == "MATCH"
    assert recommended_decision("CUSTOMER", 0.80) == "REVIEW"
    assert recommended_decision("CUSTOMER", 0.20) == "NO_MATCH"
    assert recommended_decision("VEHICLE", 0.97) == "REVIEW"
    assert recommended_decision("ACCOUNT_CUSTOMER", 0.94) == "MATCH"

