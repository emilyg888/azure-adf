"""Snowpark job for Element Fleet fuel anomaly FEATURES output.

This job reads only Snowflake CONFORMED tables and writes the MVP feature
output to FEATURES.FEATURE_FUEL_ANOMALY_SCORE. It intentionally stops at the
FEATURES layer; GOLD and SEMANTIC outputs are phase-two extensions after a
clear consumption contract is defined.
"""

from __future__ import annotations

from snowflake.snowpark import Session
from snowflake.snowpark import functions as F
from snowflake.snowpark.window import Window


TARGET_TABLE = "FEATURES.FEATURE_FUEL_ANOMALY_SCORE"


def build_feature_fuel_anomaly_score(session: Session, batch_date: str | None = None) -> str:
    """Build fuel anomaly feature rows from conformed facts and dimensions."""

    session.sql("CREATE SCHEMA IF NOT EXISTS FEATURES").collect()
    _create_target_table(session)

    fuel_txn = session.table("CONFORMED.FACT_FUEL_TRANSACTION")
    telematics = session.table("CONFORMED.FACT_TELEMATICS_DAILY_SUMMARY")
    fuel_card = session.table("CONFORMED.DIM_FUEL_CARD").filter(F.col("IS_CURRENT") == F.lit(True))
    vehicle = session.table("CONFORMED.DIM_VEHICLE").filter(F.col("IS_CURRENT") == F.lit(True))
    client = session.table("CONFORMED.DIM_CLIENT").filter(F.col("IS_CURRENT") == F.lit(True))

    if batch_date:
        fuel_txn = fuel_txn.filter(F.to_date(F.col("TRANSACTION_DATETIME")) <= F.to_date(F.lit(batch_date)))

    txn = (
        fuel_txn.select(
            F.col("FUEL_TRANSACTION_ID"),
            F.col("FUEL_CARD_ID"),
            F.col("VEHICLE_ID").alias("TXN_VEHICLE_ID"),
            F.col("CLIENT_ID").alias("TXN_CLIENT_ID"),
            F.col("TRANSACTION_DATETIME"),
            F.to_date(F.col("TRANSACTION_DATETIME")).alias("TRANSACTION_DATE"),
            F.col("MERCHANT_STATE"),
            F.col("FUEL_PRODUCT"),
            F.col("LITRES"),
            F.col("GROSS_AMOUNT"),
            F.col("EXCEPTION_FLAG"),
            F.col("SOURCE_RECORD_HASH"),
        )
        .join(
            fuel_card.select(
                F.col("FUEL_CARD_ID").alias("CARD_FUEL_CARD_ID"),
                F.col("VEHICLE_ID").alias("CARD_VEHICLE_ID"),
                F.col("CLIENT_ID").alias("CARD_CLIENT_ID"),
                F.col("CARD_STATUS"),
                F.col("MONTHLY_LIMIT_AMOUNT"),
            ),
            F.col("FUEL_CARD_ID") == F.col("CARD_FUEL_CARD_ID"),
            "left",
        )
        .join(
            vehicle.select(
                F.col("VEHICLE_SK"),
                F.col("VEHICLE_ID").alias("DIM_VEHICLE_ID"),
                F.col("CLIENT_ID").alias("VEHICLE_CLIENT_ID"),
                F.col("STATE_REGISTERED"),
                F.col("FUEL_TYPE"),
                F.col("VEHICLE_STATUS"),
            ),
            F.col("TXN_VEHICLE_ID") == F.col("DIM_VEHICLE_ID"),
            "left",
        )
        .join(
            client.select(
                F.col("CLIENT_SK"),
                F.col("CLIENT_ID").alias("DIM_CLIENT_ID"),
                F.col("CLIENT_NAME"),
                F.col("INDUSTRY_SEGMENT"),
            ),
            F.col("TXN_CLIENT_ID") == F.col("DIM_CLIENT_ID"),
            "left",
        )
    )

    usage = telematics.select(
        F.col("VEHICLE_ID").alias("TEL_VEHICLE_ID"),
        F.to_date(F.col("EVENT_DATE")).alias("TEL_EVENT_DATE"),
        F.col("DISTANCE_KM"),
    )

    enriched = txn.join(
        usage,
        (F.col("TXN_VEHICLE_ID") == F.col("TEL_VEHICLE_ID"))
        & (F.col("TRANSACTION_DATE") == F.col("TEL_EVENT_DATE")),
        "left",
    )

    rolling_window = (
        Window.partition_by("FUEL_CARD_ID")
        .order_by(F.col("TRANSACTION_DATETIME").cast("timestamp").cast("long"))
        .range_between(-7 * 24 * 60 * 60, 0)
    )
    baseline_window = Window.partition_by("FUEL_CARD_ID")

    features = (
        enriched.with_column(
            "FUEL_COST_PER_KM",
            F.iff(F.coalesce(F.col("DISTANCE_KM"), F.lit(0)) > 0, F.col("GROSS_AMOUNT") / F.col("DISTANCE_KM"), None),
        )
        .with_column("TRANSACTION_FREQUENCY_7D", F.count("FUEL_TRANSACTION_ID").over(rolling_window))
        .with_column("AVG_GROSS_AMOUNT_BY_CARD", F.avg("GROSS_AMOUNT").over(baseline_window))
        .with_column("STD_GROSS_AMOUNT_BY_CARD", F.stddev("GROSS_AMOUNT").over(baseline_window))
        .with_column("MULTIPLE_FILL_FLAG", F.col("TRANSACTION_FREQUENCY_7D") > F.lit(1))
        .with_column(
            "NO_USAGE_MATCH_FLAG",
            F.col("DISTANCE_KM").is_null() | (F.coalesce(F.col("DISTANCE_KM"), F.lit(0)) <= 0),
        )
        .with_column(
            "HIGH_VALUE_TRANSACTION_FLAG",
            (F.col("GROSS_AMOUNT") > F.lit(250))
            | (
                (F.col("STD_GROSS_AMOUNT_BY_CARD").is_not_null())
                & (F.col("GROSS_AMOUNT") > F.col("AVG_GROSS_AMOUNT_BY_CARD") + (F.lit(2) * F.col("STD_GROSS_AMOUNT_BY_CARD")))
            ),
        )
        .with_column(
            "FUEL_CARD_VEHICLE_MISMATCH_FLAG",
            (F.col("CARD_VEHICLE_ID").is_not_null() & (F.col("CARD_VEHICLE_ID") != F.col("TXN_VEHICLE_ID")))
            | (F.col("CARD_CLIENT_ID").is_not_null() & (F.col("CARD_CLIENT_ID") != F.col("TXN_CLIENT_ID"))),
        )
        .with_column(
            "FUEL_ANOMALY_SCORE",
            F.least(
                F.lit(100),
                (F.iff(F.col("HIGH_VALUE_TRANSACTION_FLAG"), F.lit(30), F.lit(0)))
                + (F.iff(F.col("NO_USAGE_MATCH_FLAG"), F.lit(25), F.lit(0)))
                + (F.iff(F.col("FUEL_CARD_VEHICLE_MISMATCH_FLAG"), F.lit(30), F.lit(0)))
                + (F.iff(F.col("MULTIPLE_FILL_FLAG"), F.lit(15), F.lit(0))),
            ),
        )
        .with_column(
            "ANOMALY_REASON_CODES",
            F.array_to_string(
                F.array_construct_compact(
                    F.iff(F.col("HIGH_VALUE_TRANSACTION_FLAG"), F.lit("HIGH_VALUE_TRANSACTION"), None),
                    F.iff(F.col("NO_USAGE_MATCH_FLAG"), F.lit("NO_USAGE_MATCH"), None),
                    F.iff(F.col("FUEL_CARD_VEHICLE_MISMATCH_FLAG"), F.lit("CARD_VEHICLE_MISMATCH"), None),
                    F.iff(F.col("MULTIPLE_FILL_FLAG"), F.lit("MULTIPLE_FILLS_7D"), None),
                ),
                F.lit(","),
            ),
        )
        .select(
            F.col("FUEL_TRANSACTION_ID"),
            F.col("FUEL_CARD_ID"),
            F.col("TXN_VEHICLE_ID").alias("VEHICLE_ID"),
            F.col("VEHICLE_SK"),
            F.col("TXN_CLIENT_ID").alias("CLIENT_ID"),
            F.col("CLIENT_SK"),
            F.col("TRANSACTION_DATETIME"),
            F.col("TRANSACTION_DATE"),
            F.col("MERCHANT_STATE"),
            F.col("FUEL_PRODUCT"),
            F.col("LITRES"),
            F.col("GROSS_AMOUNT"),
            F.col("DISTANCE_KM"),
            F.col("FUEL_COST_PER_KM"),
            F.col("TRANSACTION_FREQUENCY_7D"),
            F.col("MULTIPLE_FILL_FLAG"),
            F.col("NO_USAGE_MATCH_FLAG"),
            F.col("HIGH_VALUE_TRANSACTION_FLAG"),
            F.col("FUEL_CARD_VEHICLE_MISMATCH_FLAG"),
            F.col("FUEL_ANOMALY_SCORE"),
            F.col("ANOMALY_REASON_CODES"),
            F.lit("fuel_anomaly_rules_v0.1").alias("FEATURE_VERSION"),
            F.current_timestamp().alias("SCORED_AT"),
            F.coalesce(F.to_date(F.lit(batch_date)) if batch_date else F.col("TRANSACTION_DATE"), F.current_date()).alias("BATCH_DATE"),
            F.col("SOURCE_RECORD_HASH"),
        )
    )

    features.write.mode("overwrite").save_as_table(TARGET_TABLE)
    row_count = session.table(TARGET_TABLE).count()
    return f"Wrote {row_count} rows to {TARGET_TABLE}"


def _create_target_table(session: Session) -> None:
    session.sql(
        f"""
CREATE TABLE IF NOT EXISTS {TARGET_TABLE} (
  FUEL_TRANSACTION_ID VARCHAR,
  FUEL_CARD_ID VARCHAR,
  VEHICLE_ID VARCHAR,
  VEHICLE_SK NUMBER,
  CLIENT_ID VARCHAR,
  CLIENT_SK NUMBER,
  TRANSACTION_DATETIME TIMESTAMP_NTZ,
  TRANSACTION_DATE DATE,
  MERCHANT_STATE VARCHAR,
  FUEL_PRODUCT VARCHAR,
  LITRES NUMBER(18, 2),
  GROSS_AMOUNT NUMBER(18, 2),
  DISTANCE_KM NUMBER(18, 2),
  FUEL_COST_PER_KM NUMBER(18, 6),
  TRANSACTION_FREQUENCY_7D NUMBER,
  MULTIPLE_FILL_FLAG BOOLEAN,
  NO_USAGE_MATCH_FLAG BOOLEAN,
  HIGH_VALUE_TRANSACTION_FLAG BOOLEAN,
  FUEL_CARD_VEHICLE_MISMATCH_FLAG BOOLEAN,
  FUEL_ANOMALY_SCORE NUMBER,
  ANOMALY_REASON_CODES VARCHAR,
  FEATURE_VERSION VARCHAR,
  SCORED_AT TIMESTAMP_NTZ,
  BATCH_DATE DATE,
  SOURCE_RECORD_HASH VARCHAR
)
"""
    ).collect()


def main(session: Session) -> str:
    """Snowflake stored procedure entrypoint."""

    return build_feature_fuel_anomaly_score(session)
