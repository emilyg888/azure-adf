# Databricks notebook source
"""Baseline Databricks scorer for unresolved Fleet identity candidates.

This notebook is intentionally contract-first. It keeps Databricks responsible
for feature and score evidence while Snowflake remains the final decision
authority.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

try:
    import mlflow
except ImportError:  # Allows local syntax tests without Databricks ML runtime.
    mlflow = None


MODEL_NAME = "fleet_identity_candidate_baseline_scorer"
MODEL_VERSION = "v0"
FEATURE_VERSION = "candidate_feature_v1"
THRESHOLD_POLICY_VERSION = "v1"


ENTITY_CONFIG = {
    "CUSTOMER": {
        "candidate_table": "IDENTITY.CUSTOMER_MATCH_CANDIDATE",
        "score_table": "IDENTITY.STG_CUSTOMER_MATCH_SCORE_WRITEBACK",
    },
    "VEHICLE": {
        "candidate_table": "IDENTITY.VEHICLE_MATCH_CANDIDATE",
        "score_table": "IDENTITY.STG_VEHICLE_MATCH_SCORE_WRITEBACK",
    },
    "DEVICE_VEHICLE": {
        "candidate_table": "IDENTITY.DEVICE_VEHICLE_MATCH_CANDIDATE",
        "score_table": "IDENTITY.STG_DEVICE_VEHICLE_MATCH_SCORE_WRITEBACK",
    },
    "ACCOUNT_CUSTOMER": {
        "candidate_table": "IDENTITY.ACCOUNT_CUSTOMER_MATCH_CANDIDATE",
        "score_table": "IDENTITY.STG_ACCOUNT_CUSTOMER_MATCH_SCORE_WRITEBACK",
    },
}


def recommended_decision(entity_type: str, score: float) -> str:
    thresholds = {
        "CUSTOMER": (0.95, 0.70),
        "VEHICLE": (0.98, 0.80),
        "DEVICE_VEHICLE": (0.96, 0.75),
        "ACCOUNT_CUSTOMER": (0.93, 0.65),
    }
    auto_match, review_min = thresholds[entity_type]
    if score >= auto_match:
        return "MATCH"
    if score >= review_min:
        return "REVIEW"
    return "NO_MATCH"


def score_candidates(candidate_rows: list[dict[str, object]], scoring_run_id: str, mlflow_run_id: str) -> list[dict[str, object]]:
    scored_at = datetime.now(timezone.utc).isoformat()
    outputs = []
    for row in candidate_rows:
        entity_type = str(row["ENTITY_TYPE"]).upper()
        match_score = float(row.get("MATCH_SCORE") or 0.0)
        outputs.append(
            {
                "CANDIDATE_PAIR_ID": row["CANDIDATE_ID"],
                "ENTITY_TYPE": entity_type,
                "MATCH_SCORE": match_score,
                "RECOMMENDED_DECISION": recommended_decision(entity_type, match_score),
                "REASON_CODES": [row.get("MATCH_REASON_CODE", "baseline_candidate_score")],
                "MODEL_NAME": MODEL_NAME,
                "MODEL_VERSION": MODEL_VERSION,
                "MLFLOW_RUN_ID": mlflow_run_id,
                "SCORING_RUN_ID": scoring_run_id,
                "FEATURE_SNAPSHOT_ID": f"{FEATURE_VERSION}_{scoring_run_id}",
                "SCORED_AT": scored_at,
                "WRITEBACK_BATCH_ID": scoring_run_id,
            }
        )
    return outputs


def run_snowflake_writeback(spark, sf_options: dict[str, str]) -> str:
    scoring_run_id = f"score_{uuid4().hex}"
    mlflow_run_id = scoring_run_id

    if mlflow is not None:
        with mlflow.start_run(run_name=scoring_run_id) as run:
            mlflow_run_id = run.info.run_id
            mlflow.log_param("model_name", MODEL_NAME)
            mlflow.log_param("model_version", MODEL_VERSION)
            mlflow.log_param("feature_version", FEATURE_VERSION)
            mlflow.log_param("threshold_policy_version", THRESHOLD_POLICY_VERSION)
            _score_all_entities(spark, sf_options, scoring_run_id, mlflow_run_id)
    else:
        _score_all_entities(spark, sf_options, scoring_run_id, mlflow_run_id)

    return scoring_run_id


def _score_all_entities(spark, sf_options: dict[str, str], scoring_run_id: str, mlflow_run_id: str) -> None:
    for config in ENTITY_CONFIG.values():
        candidates = (
            spark.read.format("snowflake")
            .options(**sf_options)
            .option("dbtable", config["candidate_table"])
            .load()
            .where("AUTO_MATCH_FLAG = FALSE OR REVIEW_REQUIRED_FLAG = TRUE")
        )
        rows = [row.asDict() for row in candidates.collect()]
        scored_rows = score_candidates(rows, scoring_run_id, mlflow_run_id)
        if scored_rows:
            spark.createDataFrame(scored_rows).write.format("snowflake").options(**sf_options).option(
                "dbtable", config["score_table"]
            ).mode("append").save()

