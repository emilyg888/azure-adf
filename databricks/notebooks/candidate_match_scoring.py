# Databricks notebook source
"""Baseline Databricks scorer for unresolved Fleet identity candidates.

This notebook is intentionally contract-first. It keeps Databricks responsible
for feature and score evidence while Snowflake remains the final decision
authority.
"""

from __future__ import annotations

import base64
import subprocess
import sys
from datetime import datetime, timezone
from uuid import uuid4

from cryptography.hazmat.primitives import serialization

try:
    import mlflow
except ImportError:  # Allows local syntax tests without Databricks ML runtime.
    mlflow = None

MODEL_NAME = "fleet_identity_candidate_baseline_scorer"
MODEL_VERSION = "v0"
FEATURE_VERSION = "candidate_feature_v1"
THRESHOLD_POLICY_VERSION = "v1"

SCORE_COLUMNS = [
    "CANDIDATE_PAIR_ID",
    "ENTITY_TYPE",
    "MATCH_SCORE",
    "RECOMMENDED_DECISION",
    "REASON_CODES",
    "MODEL_NAME",
    "MODEL_VERSION",
    "MLFLOW_RUN_ID",
    "SCORING_RUN_ID",
    "FEATURE_SNAPSHOT_ID",
    "SCORED_AT",
    "WRITEBACK_BATCH_ID",
]


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


def build_sf_options(dbutils) -> dict[str, str]:
    dbutils.widgets.text("snowflake_secret_scope", "fleet-snowflake")
    dbutils.widgets.text("snowflake_database", "FLEET_MVP_SIT")
    dbutils.widgets.text("snowflake_schema", "IDENTITY")

    secret_scope = dbutils.widgets.get("snowflake_secret_scope")
    snowflake_database = dbutils.widgets.get("snowflake_database")
    snowflake_schema = dbutils.widgets.get("snowflake_schema")
    private_key = dbutils.secrets.get(secret_scope, "private_key")
    private_key_passphrase = dbutils.secrets.get(secret_scope, "private_key_passphrase")
    formatted_private_key = format_private_key_for_snowflake(private_key, private_key_passphrase)

    return {
        "host": normalize_snowflake_host(dbutils.secrets.get(secret_scope, "account")),
        "sfUser": dbutils.secrets.get(secret_scope, "user"),
        "pem_private_key": formatted_private_key,
        "private_key_der": format_private_key_body_as_der(formatted_private_key),
        "sfRole": dbutils.secrets.get(secret_scope, "role"),
        "sfWarehouse": dbutils.secrets.get(secret_scope, "warehouse"),
        "sfDatabase": snowflake_database,
        "sfSchema": snowflake_schema,
    }


def normalize_snowflake_host(account: str) -> str:
    return account.strip().removeprefix("https://").removeprefix("http://").rstrip("/")


def format_private_key_for_snowflake(private_key_pem: str, passphrase: str | None = None) -> str:
    normalized_secret = private_key_pem.strip().replace("\\n", "\n")
    if "PRIVATE KEY" not in normalized_secret:
        key_body = "".join(normalized_secret.split())
        if not key_body.startswith("MII"):
            raise ValueError("Snowflake private key body is not PKCS8 PEM base64.")
        return key_body

    password = passphrase.encode("utf-8") if passphrase and "ENCRYPTED" in private_key_pem else None
    private_key = serialization.load_pem_private_key(
        normalized_secret.encode("utf-8"),
        password=password,
    )
    unencrypted_pkcs8 = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    key_body = "".join(
        line.strip()
        for line in unencrypted_pkcs8.splitlines()
        if line.strip() and "PRIVATE KEY" not in line
    )
    if not key_body.startswith("MII"):
        raise ValueError("Snowflake private key body is not PKCS8 PEM base64.")
    return key_body


def format_private_key_body_as_der(key_body: str) -> bytes:
    padding = "=" * (-len(key_body) % 4)
    return base64.b64decode(key_body + padding)


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
    spark_sf_options = spark_snowflake_options(sf_options)

    if mlflow is not None:
        with mlflow.start_run(run_name=scoring_run_id) as run:
            mlflow_run_id = run.info.run_id
            mlflow.log_param("model_name", MODEL_NAME)
            mlflow.log_param("model_version", MODEL_VERSION)
            mlflow.log_param("feature_version", FEATURE_VERSION)
            mlflow.log_param("threshold_policy_version", THRESHOLD_POLICY_VERSION)
            _score_all_entities(spark, spark_sf_options, scoring_run_id, mlflow_run_id)
    else:
        _score_all_entities(spark, spark_sf_options, scoring_run_id, mlflow_run_id)

    call_snowflake_procedure(
        spark,
        sf_options,
        f"CALL IDENTITY.MERGE_MATCH_SCORE_WRITEBACK('{scoring_run_id}')",
    )
    call_snowflake_procedure(
        spark,
        sf_options,
        f"CALL IDENTITY.APPLY_MATCH_DECISION_POLICY('{scoring_run_id}')",
    )

    return scoring_run_id


def call_snowflake_procedure(spark, sf_options: dict[str, str], sql: str) -> None:
    connector = import_snowflake_connector()
    account = sf_options["host"].replace(".snowflakecomputing.com", "")
    with connector.connect(
        account=account,
        user=sf_options["sfUser"],
        private_key=sf_options["private_key_der"],
        role=sf_options["sfRole"],
        warehouse=sf_options["sfWarehouse"],
        database=sf_options["sfDatabase"],
        schema=sf_options["sfSchema"],
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)


def spark_snowflake_options(sf_options: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in sf_options.items() if key != "private_key_der"}


def import_snowflake_connector():
    try:
        import snowflake.connector

        return snowflake.connector
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "snowflake-connector-python"])
        import snowflake.connector

        return snowflake.connector


def build_score_schema():
    from pyspark.sql.types import ArrayType, DoubleType, StringType, StructField, StructType

    return StructType(
        [
            StructField("CANDIDATE_PAIR_ID", StringType(), False),
            StructField("ENTITY_TYPE", StringType(), False),
            StructField("MATCH_SCORE", DoubleType(), False),
            StructField("RECOMMENDED_DECISION", StringType(), False),
            StructField("REASON_CODES", ArrayType(StringType()), False),
            StructField("MODEL_NAME", StringType(), False),
            StructField("MODEL_VERSION", StringType(), False),
            StructField("MLFLOW_RUN_ID", StringType(), False),
            StructField("SCORING_RUN_ID", StringType(), False),
            StructField("FEATURE_SNAPSHOT_ID", StringType(), False),
            StructField("SCORED_AT", StringType(), False),
            StructField("WRITEBACK_BATCH_ID", StringType(), False),
        ]
    )


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
            score_df = spark.createDataFrame(scored_rows, schema=build_score_schema()).select(*SCORE_COLUMNS)
            score_df.write.format("snowflake").options(**sf_options).option(
                "dbtable", config["score_table"]
            ).mode("append").save()


if "dbutils" in globals() and "spark" in globals():
    run_snowflake_writeback(spark, build_sf_options(dbutils))
