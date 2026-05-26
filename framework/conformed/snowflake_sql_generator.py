"""Snowflake SQL generation for deterministic CONFORMED modelling."""

from __future__ import annotations


def create_external_table_sql(*, table_name: str, stage_path: str, columns: list[str]) -> str:
    select_list = ",\n  ".join(
        f"VALUE:c{index + 1}::{_snowflake_type(column)} AS {column.upper()}"
        for index, column in enumerate(columns)
    )
    return f"""CREATE OR REPLACE EXTERNAL TABLE STG_FLEET.{table_name.upper()}_EXT (
  {select_list}
)
WITH LOCATION = @{stage_path}
FILE_FORMAT = (TYPE = PARQUET)
AUTO_REFRESH = FALSE;"""


def create_transient_staging_load_sql(*, table_name: str, external_table_name: str) -> str:
    return f"""CREATE OR REPLACE TRANSIENT TABLE STG_FLEET.{table_name.upper()} AS
SELECT *
FROM STG_FLEET.{external_table_name.upper()};"""


def scd2_dimension_merge_sql(
    *,
    staging_table: str,
    dimension_table: str,
    business_key: str,
    attribute_columns: list[str],
    foreign_key_checks: dict[str, tuple[str, str]] | None = None,
    batch_timestamp_param: str = ":batch_timestamp",
) -> str:
    columns = [business_key, *attribute_columns]
    source_columns = ", ".join(f"SRC.{column.upper()}" for column in columns)
    target_columns = ", ".join(column.upper() for column in columns)
    eligible_source = _eligible_mutable_source_sql(
        staging_table=staging_table,
        foreign_key_checks=foreign_key_checks or {},
    )
    return f"""-- Expire changed current rows.
UPDATE CONFORMED.{dimension_table.upper()} TGT
SET
  EFFECTIVE_TO = SRC.EFFECTIVE_AT,
  IS_CURRENT = FALSE,
  UPDATED_AT = CURRENT_TIMESTAMP()
FROM (
{eligible_source}
) SRC
WHERE TGT.{business_key.upper()} = SRC.{business_key.upper()}
  AND TGT.IS_CURRENT = TRUE
  AND SRC._DELTA_ACTION <> 'DELETE'
  AND TGT.SOURCE_RECORD_HASH <> SRC._RECORD_HASH;

-- Insert new current rows for new or changed business keys.
INSERT INTO CONFORMED.{dimension_table.upper()} (
  {target_columns},
  BUSINESS_KEY,
  EFFECTIVE_FROM,
  EFFECTIVE_TO,
  IS_CURRENT,
  DELETED_FLAG,
  SOURCE_EFFECTIVE_AT,
  SOURCE_UPDATED_AT,
  SOURCE_RECORD_HASH,
  CREATED_AT,
  UPDATED_AT
)
SELECT
  {source_columns},
  SRC.{business_key.upper()} AS BUSINESS_KEY,
  SRC.EFFECTIVE_AT AS EFFECTIVE_FROM,
  '9999-12-31'::TIMESTAMP_NTZ AS EFFECTIVE_TO,
  TRUE AS IS_CURRENT,
  FALSE AS DELETED_FLAG,
  SRC.EFFECTIVE_AT AS SOURCE_EFFECTIVE_AT,
  SRC.UPDATED_AT AS SOURCE_UPDATED_AT,
  SRC._RECORD_HASH AS SOURCE_RECORD_HASH,
  CURRENT_TIMESTAMP() AS CREATED_AT,
  CURRENT_TIMESTAMP() AS UPDATED_AT
FROM (
{eligible_source}
) SRC
LEFT JOIN CONFORMED.{dimension_table.upper()} TGT
  ON TGT.{business_key.upper()} = SRC.{business_key.upper()}
 AND TGT.IS_CURRENT = TRUE
WHERE SRC._DELTA_ACTION <> 'DELETE'
  AND (TGT.{business_key.upper()} IS NULL OR TGT.SOURCE_RECORD_HASH <> SRC._RECORD_HASH);

-- Soft-delete missing rows for authoritative full snapshots only.
UPDATE CONFORMED.{dimension_table.upper()} TGT
SET
  EFFECTIVE_TO = {batch_timestamp_param},
  IS_CURRENT = FALSE,
  DELETED_FLAG = TRUE,
  UPDATED_AT = CURRENT_TIMESTAMP()
WHERE TGT.IS_CURRENT = TRUE
  AND NOT EXISTS (
    SELECT 1
    FROM STG_FLEET.{staging_table.upper()} SRC
    WHERE SRC.{business_key.upper()} = TGT.{business_key.upper()}
      AND SRC._LOAD_TYPE = 'full'
  )
  AND EXISTS (
    SELECT 1
    FROM STG_FLEET.{staging_table.upper()} SRC
    WHERE SRC._LOAD_TYPE = 'full'
  );"""


def append_only_fact_merge_sql(*, staging_table: str, fact_table: str, event_key: str, columns: list[str]) -> str:
    target_columns = ", ".join(column.upper() for column in [*columns, "event_business_key", "source_record_hash"])
    source_columns = ", ".join(f"SRC.{column.upper()}" for column in columns)
    return f"""MERGE INTO CONFORMED.{fact_table.upper()} TGT
USING (
  SELECT *
  FROM STG_FLEET.{staging_table.upper()}
  WHERE _IS_EXACT_DUPLICATE = FALSE
    AND COALESCE(_DQ_STATUS, 'passed') = 'passed'
) SRC
ON TGT.{event_key.upper()} = SRC.{event_key.upper()}
WHEN NOT MATCHED THEN INSERT (
  {target_columns}
) VALUES (
  {source_columns},
  SRC.{event_key.upper()},
  SRC._RECORD_HASH
);"""


def version_history_merge_sql(*, staging_table: str, history_table: str, business_key: str, columns: list[str]) -> str:
    target_columns = ", ".join(
        column.upper()
        for column in [*columns, "event_business_key", "source_updated_at", "source_record_hash", "delta_action"]
    )
    source_columns = ", ".join(f"SRC.{column.upper()}" for column in columns)
    return f"""MERGE INTO CONFORMED.{history_table.upper()} TGT
USING (
  SELECT *
  FROM STG_FLEET.{staging_table.upper()}
  WHERE _IS_EXACT_DUPLICATE = FALSE
    AND COALESCE(_DQ_STATUS, 'passed') = 'passed'
) SRC
ON TGT.EVENT_BUSINESS_KEY = SRC.{business_key.upper()}
AND TGT.SOURCE_UPDATED_AT = SRC.UPDATED_AT
AND TGT.SOURCE_RECORD_HASH = SRC._RECORD_HASH
WHEN NOT MATCHED THEN INSERT (
  {target_columns}
) VALUES (
  {source_columns},
  SRC.{business_key.upper()},
  SRC.UPDATED_AT,
  SRC._RECORD_HASH,
  SRC._DELTA_ACTION
);"""


def referential_integrity_check_sql(
    *,
    staging_table: str,
    parent_table: str,
    child_key: str,
    parent_key: str,
) -> str:
    return f"""SELECT SRC.*
FROM STG_FLEET.{staging_table.upper()} SRC
LEFT JOIN CONFORMED.{parent_table.upper()} PARENT
  ON PARENT.{parent_key.upper()} = SRC.{child_key.upper()}
 AND PARENT.IS_CURRENT = TRUE
WHERE SRC.{child_key.upper()} IS NOT NULL
  AND PARENT.{parent_key.upper()} IS NULL;"""


def event_summary_rebuild_sql(
    *,
    staging_table: str,
    summary_table: str,
    batch_date_param: str = ":batch_date",
) -> str:
    return f"""DELETE FROM CONFORMED.{summary_table.upper()}
WHERE BATCH_DATE = {batch_date_param};

INSERT INTO CONFORMED.{summary_table.upper()} (
  CLIENT_ID,
  VEHICLE_ID,
  EVENT_DATE,
  EVENT_COUNT,
  BATCH_DATE
)
SELECT
  CLIENT_ID,
  VEHICLE_ID,
  CAST(EVENT_DATETIME AS DATE) AS EVENT_DATE,
  COUNT(*) AS EVENT_COUNT,
  {batch_date_param} AS BATCH_DATE
FROM STG_FLEET.{staging_table.upper()}
WHERE _BATCH_DATE = {batch_date_param}
  AND _IS_EXACT_DUPLICATE = FALSE
  AND COALESCE(_DQ_STATUS, 'passed') = 'passed'
GROUP BY CLIENT_ID, VEHICLE_ID, CAST(EVENT_DATETIME AS DATE);"""


def _eligible_mutable_source_sql(*, staging_table: str, foreign_key_checks: dict[str, tuple[str, str]]) -> str:
    joins = []
    filters = [
        "  SRC._IS_LATEST_FOR_BUSINESS_KEY = TRUE",
        "  AND SRC._LATEST_RESOLUTION_STATUS = 'resolved'",
        "  AND SRC._IS_EXACT_DUPLICATE = FALSE",
        "  AND COALESCE(SRC._DQ_STATUS, 'passed') = 'passed'",
    ]
    for child_key, (parent_table, parent_key) in foreign_key_checks.items():
        alias = f"PARENT_{child_key.upper()}"
        joins.append(
            f"LEFT JOIN CONFORMED.{parent_table.upper()} {alias}\n"
            f"  ON {alias}.{parent_key.upper()} = SRC.{child_key.upper()}\n"
            f" AND {alias}.IS_CURRENT = TRUE"
        )
        filters.append(f"  AND {alias}.{parent_key.upper()} IS NOT NULL")
    join_sql = "\n".join(joins)
    where_sql = "\n".join(filters)
    return f"""  SELECT SRC.*
  FROM STG_FLEET.{staging_table.upper()} SRC
{join_sql}
  WHERE
{where_sql}"""


def _snowflake_type(column: str) -> str:
    if column.endswith("_amount") or column in {"gross_amount", "litres", "energy_kwh"}:
        return "NUMBER"
    if column.endswith("_date"):
        return "DATE"
    if column.endswith("_datetime") or column.endswith("_at"):
        return "TIMESTAMP_NTZ"
    return "VARCHAR"
