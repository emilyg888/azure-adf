from framework.conformed.snowflake_sql_generator import (
    append_only_fact_merge_sql,
    create_external_table_sql,
    create_transient_staging_load_sql,
    event_summary_rebuild_sql,
    referential_integrity_check_sql,
    scd2_dimension_merge_sql,
    version_history_merge_sql,
)


def test_external_table_and_transient_staging_sql():
    external_sql = create_external_table_sql(
        table_name="clients",
        stage_path="ADLS_STAGING_STAGE/domain=fleet_management/dataset=clients/",
        columns=["client_id", "updated_at"],
    )
    transient_sql = create_transient_staging_load_sql(
        table_name="clients",
        external_table_name="clients_ext",
    )

    assert "CREATE OR REPLACE EXTERNAL TABLE STG_FLEET.CLIENTS_EXT" in external_sql
    assert "FILE_FORMAT = (TYPE = PARQUET)" in external_sql
    assert "CREATE OR REPLACE TRANSIENT TABLE STG_FLEET.CLIENTS" in transient_sql
    assert "FROM STG_FLEET.CLIENTS_EXT" in transient_sql


def test_scd2_dimension_merge_sql_includes_soft_delete_for_full_extracts():
    sql = scd2_dimension_merge_sql(
        staging_table="clients",
        dimension_table="dim_client",
        business_key="client_id",
        attribute_columns=["client_name", "client_status"],
        foreign_key_checks={"client_id": ("dim_client_parent", "client_id")},
    )

    assert "UPDATE CONFORMED.DIM_CLIENT TGT" in sql
    assert "TGT.SOURCE_RECORD_HASH <> SRC._RECORD_HASH" in sql
    assert "DELETED_FLAG = TRUE" in sql
    assert "SRC._LOAD_TYPE = 'full'" in sql
    assert "SRC._LATEST_RESOLUTION_STATUS = 'resolved'" in sql
    assert "SRC._IS_EXACT_DUPLICATE = FALSE" in sql
    assert "COALESCE(SRC._DQ_STATUS, 'passed') = 'passed'" in sql
    assert "LEFT JOIN CONFORMED.DIM_CLIENT_PARENT" in sql
    assert "PARENT_CLIENT_ID.CLIENT_ID IS NOT NULL" in sql


def test_fact_history_ri_and_summary_sql():
    fact_sql = append_only_fact_merge_sql(
        staging_table="telematics_daily",
        fact_table="fact_telematics_daily_summary",
        event_key="telematics_event_id",
        columns=["telematics_event_id", "vehicle_id", "client_id"],
    )
    history_sql = version_history_merge_sql(
        staging_table="leasing_contracts",
        history_table="hist_lease_contract_version",
        business_key="lease_id",
        columns=["lease_id", "vehicle_id", "client_id"],
    )
    ri_sql = referential_integrity_check_sql(
        staging_table="vehicles",
        parent_table="dim_client",
        child_key="client_id",
        parent_key="client_id",
    )
    summary_sql = event_summary_rebuild_sql(
        staging_table="driver_app_events",
        summary_table="fact_driver_app_daily_summary",
    )

    assert "MERGE INTO CONFORMED.FACT_TELEMATICS_DAILY_SUMMARY" in fact_sql
    assert "WHEN NOT MATCHED THEN INSERT" in fact_sql
    assert "COALESCE(_DQ_STATUS, 'passed') = 'passed'" in fact_sql
    assert "MERGE INTO CONFORMED.HIST_LEASE_CONTRACT_VERSION" in history_sql
    assert "TGT.SOURCE_UPDATED_AT = SRC.UPDATED_AT" in history_sql
    assert "COALESCE(_DQ_STATUS, 'passed') = 'passed'" in history_sql
    assert "LEFT JOIN CONFORMED.DIM_CLIENT" in ri_sql
    assert "PARENT.IS_CURRENT = TRUE" in ri_sql
    assert "DELETE FROM CONFORMED.FACT_DRIVER_APP_DAILY_SUMMARY" in summary_sql
    assert "COALESCE(_DQ_STATUS, 'passed') = 'passed'" in summary_sql
    assert "GROUP BY CLIENT_ID, VEHICLE_ID, CAST(EVENT_DATETIME AS DATE)" in summary_sql
