from pathlib import Path

import pytest


SQL_PATH = Path("metadata/ddl/fleet_customer360_identity_resolution.sql")
SIT_SQL_PATH = Path("metadata/ddl/fleet_snowflake_sit_setup.sql")
VEHICLE_STREAM_SQL_PATH = Path("metadata/ddl/fleet_snowflake_stream_dim_vehicle.sql")
STAGING_INPUTS_SQL_PATH = Path("metadata/ddl/fleet_snowflake_staging_identity_inputs.sql")
REBUILD_ORDER_SQL_PATH = Path("metadata/ddl/fleet_customer360_rebuild_order.sql")
LOCAL_BUILDER_PATH = Path("scripts/fleet_build_customer360_local.py")
SOURCE_METADATA_PATH = Path("/Users/emilygao/LocalDocuments/Projects/bb_datasets/fleet-services/metadata.json")


def test_customer360_identity_resolution_artifact_contains_required_layers():
    sql = SQL_PATH.read_text(encoding="utf-8")

    for schema in [
        "IDENTITY",
        "GOLDEN",
        "GOLD",
        "SEMANTIC",
        "GOVERNANCE",
        "AUDIT",
    ]:
        assert f"CREATE SCHEMA IF NOT EXISTS {schema}" in sql

    assert "CREATE OR REPLACE PROCEDURE IDENTITY.BUILD_CUSTOMER360_IDENTITY" in sql
    assert "CREATE TABLE IF NOT EXISTS IDENTITY.STD_CUSTOMER" in sql
    assert "CREATE TABLE IF NOT EXISTS IDENTITY.STD_VEHICLE" in sql
    assert "CREATE TABLE IF NOT EXISTS IDENTITY.CUSTOMER_MATCH_CANDIDATE" in sql
    assert "CREATE TABLE IF NOT EXISTS GOLDEN.GOLDEN_CUSTOMER" in sql
    assert "CREATE TABLE IF NOT EXISTS GOLDEN.GOLDEN_VEHICLE" in sql
    assert "CREATE TABLE IF NOT EXISTS GOLDEN.XREF_CUSTOMER_SOURCE" in sql
    assert "CREATE TABLE IF NOT EXISTS GOLDEN.REL_CUSTOMER_VEHICLE" in sql
    assert "CREATE TABLE IF NOT EXISTS GOVERNANCE.IDENTITY_REVIEW_QUEUE" in sql
    assert "CREATE TABLE IF NOT EXISTS GOLD.CUSTOMER_360_MART" in sql
    assert "CREATE OR REPLACE VIEW SEMANTIC.CUSTOMER_360" in sql
    assert "CREATE OR REPLACE VIEW IDENTITY.GRAPH_ELIGIBLE_MATCH_DECISION" in sql


def test_customer360_identity_resolution_includes_design_guardrails():
    sql = SQL_PATH.read_text(encoding="utf-8")

    assert "deterministic_source_customer_id" in sql
    assert "fuzzy_name_state" in sql
    assert "EDITDISTANCE" in sql
    assert "MATCH_SCORE >= 0.70 AND MATCH_SCORE < 0.95" in sql
    assert "REVIEW_REQUIRED_FLAG = TRUE" in sql
    assert "SURVIVORSHIP_RULE_VERSION" in sql
    assert "IDENTITY_RESOLUTION_CONFIDENCE" in sql
    assert "CUSTOMER360_GOLDEN_CUSTOMER_WITHOUT_XREF" in sql
    assert "CUSTOMER360_CONFIDENCE_MISSING" in sql
    assert "DATA_QUALITY_STATUS = 'certified'" in sql
    assert ":RUN_ID AS CREATED_RUN_ID" in sql
    assert "COALESCE(:BATCH_DATE, CURRENT_DATE())" in sql
    assert "FINAL_DECISION = 'MATCH'" in sql
    assert "DECISION_STATUS IN ('AUTO_APPROVED', 'HUMAN_APPROVED')" in sql
    assert "GRAPH_APPLY_STATUS = 'READY_TO_APPLY'" in sql


def test_databricks_aligned_v1_matching_tables_exist():
    sql = SQL_PATH.read_text(encoding="utf-8")

    for table in [
        "IDENTITY.CUSTOMER_MATCH_FEATURE",
        "IDENTITY.VEHICLE_MATCH_FEATURE",
        "IDENTITY.DEVICE_VEHICLE_MATCH_FEATURE",
        "IDENTITY.ACCOUNT_CUSTOMER_MATCH_FEATURE",
        "IDENTITY.CUSTOMER_MATCH_SCORE",
        "IDENTITY.VEHICLE_MATCH_SCORE",
        "IDENTITY.DEVICE_VEHICLE_MATCH_SCORE",
        "IDENTITY.ACCOUNT_CUSTOMER_MATCH_SCORE",
        "IDENTITY.CUSTOMER_MATCH_DECISION",
        "IDENTITY.VEHICLE_MATCH_DECISION",
        "IDENTITY.DEVICE_VEHICLE_MATCH_DECISION",
        "IDENTITY.ACCOUNT_CUSTOMER_MATCH_DECISION",
        "IDENTITY.MATCH_REVIEW_QUEUE",
        "IDENTITY.MATCH_SCORING_RUN_AUDIT",
        "IDENTITY.MATCH_THRESHOLD_POLICY",
        "IDENTITY.MATCH_MODEL_REGISTRY_AUDIT",
    ]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql


def test_databricks_aligned_v1_writeback_and_policy_controls_exist():
    sql = SQL_PATH.read_text(encoding="utf-8")

    assert "CREATE OR REPLACE PROCEDURE IDENTITY.MERGE_MATCH_SCORE_WRITEBACK" in sql
    assert "CREATE OR REPLACE PROCEDURE IDENTITY.APPLY_MATCH_DECISION_POLICY" in sql
    assert "CANDIDATE_PAIR_ID = S.CANDIDATE_PAIR_ID" in sql
    assert "T.MODEL_VERSION = S.MODEL_VERSION" in sql
    assert "T.SCORING_RUN_ID = S.SCORING_RUN_ID" in sql
    assert "THRESHOLD_POLICY_VERSION" in sql
    assert "WRITEBACK_BATCH_ID" in sql
    assert "MLFLOW_RUN_ID" in sql


def test_customer360_consumes_exposed_fleet_identity_columns():
    sql = SQL_PATH.read_text(encoding="utf-8")

    for token in [
        "REGEXP_REPLACE(COALESCE(ABN",
        "LOWER(TRIM(EMAIL_DOMAIN))",
        "ADDRESS_LINE_1",
        "STD_TELEMATICS_DEVICE_ID",
        "STG_FLEET.TELEMATICS_DAILY",
        "STG_FLEET.INSURANCE_CLAIMS",
        "STG_FLEET.FINANCE_BILLING_INVOICES",
        "STG_FLEET.CRM_CLIENT_PORTAL_EVENTS",
        "STG_FLEET.EV_CHARGING_SESSIONS",
        "GOLDEN.REL_VEHICLE_TELEMATICS_DEVICE",
    ]:
        assert token in sql


def test_bb_dataset_metadata_exposes_customer360_inputs():
    if not SOURCE_METADATA_PATH.exists():
        pytest.skip("Fleet bb_datasets source is not present on this machine")

    import json

    metadata = json.loads(SOURCE_METADATA_PATH.read_text(encoding="utf-8"))
    tables = metadata["tables"]

    assert {"abn", "email_domain", "address_line_1", "postcode"}.issubset(tables["clients.csv"]["columns"])
    assert {"vin", "registration_plate", "telematics_device_id"}.issubset(tables["vehicles.csv"]["columns"])
    assert {"claim_id", "claim_handler_email_domain"}.issubset(tables["insurance_claims.csv"]["columns"])
    assert {"invoice_id", "billing_contact_email_domain"}.issubset(tables["finance_billing_invoices.csv"]["columns"])
    assert {"portal_event_id", "client_contact_email_domain"}.issubset(tables["crm_client_portal_events.csv"]["columns"])
    assert {"charging_session_id", "charger_serial_number", "energy_kwh"}.issubset(
        tables["ev_charging_sessions.csv"]["columns"]
    )


def test_snowflake_client_vehicle_layers_include_identity_columns():
    client_sql = SIT_SQL_PATH.read_text(encoding="utf-8")
    vehicle_sql = VEHICLE_STREAM_SQL_PATH.read_text(encoding="utf-8")

    for token in ["ABN", "EMAIL_DOMAIN", "ADDRESS_LINE_1", "POSTCODE"]:
        assert token in client_sql
    for token in ["VIN", "REGISTRATION_PLATE", "TELEMATICS_DEVICE_ID", "TELEMATICS_INSTALL_DATE"]:
        assert token in vehicle_sql


def test_snowflake_staging_inputs_cover_customer360_operational_datasets():
    sql = STAGING_INPUTS_SQL_PATH.read_text(encoding="utf-8")

    for table in [
        "LEASING_CONTRACTS",
        "FUEL_CARDS",
        "FUEL_CARD_TRANSACTIONS",
        "TELEMATICS_DAILY",
        "MAINTENANCE_WORK_ORDERS",
        "INSURANCE_CLAIMS",
        "FINANCE_BILLING_INVOICES",
        "CRM_CLIENT_PORTAL_EVENTS",
        "EV_CHARGING_SESSIONS",
    ]:
        assert f"CREATE OR REPLACE EXTERNAL TABLE STG_FLEET.{table}_EXT" in sql
        assert f"CREATE OR REPLACE TRANSIENT TABLE STG_FLEET.{table}" in sql


def test_customer360_rebuild_order_and_local_builder_exist():
    rebuild_sql = REBUILD_ORDER_SQL_PATH.read_text(encoding="utf-8")
    local_builder = LOCAL_BUILDER_PATH.read_text(encoding="utf-8")

    assert "CALL IDENTITY.BUILD_CUSTOMER360_IDENTITY" in rebuild_sql
    assert "CUSTOMER360_IDENTITY_FIELDS_POPULATED" in rebuild_sql
    assert "fleet_snowflake_sit_setup.sql" in rebuild_sql
    assert "fleet_snowflake_stream_dim_vehicle.sql" in rebuild_sql
    assert "fleet_snowflake_staging_identity_inputs.sql" in rebuild_sql
    assert "merge_scd2_dimension" in local_builder
    assert "identity_std_customer" in local_builder
    assert "semantic_customer_360" in local_builder
