# Databricks Snowflake Candidate Matching Setup

## Purpose

This guide describes the next practical build step for the Databricks-aligned candidate matching path:

1. Add a Databricks asset bundle and job config.
2. Add a Snowflake connector config template using Databricks secret names.
3. Wire the scoring notebook to call Snowflake writeback and decision procedures after score output is written.

The intended control model remains:

```text
Databricks produces scores.
Snowflake owns final decisions.
Only approved MATCH decisions are graph eligible.
```

## Prerequisites

Confirm these are available before wiring the runtime:

- Databricks workspace access.
- Databricks CLI configured locally for the target workspace.
- A Databricks cluster or serverless policy that can install the Snowflake Spark connector and JDBC driver.
- Snowflake account, role, warehouse, database, and schema for `FLEET_MVP_SIT.IDENTITY`.
- Snowflake permissions to read candidate tables, write staging score tables, and call identity procedures.
- A Databricks secret scope for Snowflake connection values.
- Network path from Databricks to Snowflake, including allow-list or private connectivity if required.

## Target Repo Files

Add or update these files:

```text
databricks/bundles/candidate_matching/databricks.yml
databricks/jobs/candidate_matching_job.yml
databricks/config/snowflake_candidate_matching.example.yml
databricks/notebooks/candidate_match_scoring.py
```

The existing notebook is:

```text
databricks/notebooks/candidate_match_scoring.py
```

## Step 1: Create the Databricks Bundle

Create `databricks/bundles/candidate_matching/databricks.yml`.

Recommended minimum structure:

```yaml
bundle:
  name: candidate-matching

include:
  - ../../jobs/candidate_matching_job.yml

targets:
  dev:
    mode: development
    default: true
    workspace:
      host: ${var.databricks_host}

variables:
  databricks_host:
    description: Databricks workspace URL.
  snowflake_secret_scope:
    default: fleet-snowflake
  snowflake_database:
    default: FLEET_MVP_SIT
  snowflake_schema:
    default: IDENTITY
```

Keep environment-specific values in Databricks bundle variables or deployment configuration, not in source code.

## Step 2: Create the Job Config

Create `databricks/jobs/candidate_matching_job.yml`.

Recommended minimum job:

```yaml
resources:
  jobs:
    candidate_matching_score_writeback:
      name: candidate-matching-score-writeback
      tasks:
        - task_key: score_candidates
          notebook_task:
            notebook_path: ../../notebooks/candidate_match_scoring.py
            base_parameters:
              snowflake_secret_scope: ${var.snowflake_secret_scope}
              snowflake_database: ${var.snowflake_database}
              snowflake_schema: ${var.snowflake_schema}
          new_cluster:
            spark_version: 15.4.x-scala2.12
            node_type_id: i3.xlarge
            num_workers: 1
            data_security_mode: SINGLE_USER
            spark_conf:
              spark.databricks.delta.preview.enabled: "true"
            libraries:
              - maven:
                  coordinates: net.snowflake:spark-snowflake_2.12:2.16.0-spark_3.4
              - maven:
                  coordinates: net.snowflake:snowflake-jdbc:3.16.1
```

Validate connector versions against the actual Databricks Runtime selected for the workspace.

## Step 3: Create the Snowflake Config Template

Create `databricks/config/snowflake_candidate_matching.example.yml`.

Use secret names, not secret values:

```yaml
snowflake:
  secret_scope: fleet-snowflake
  account_secret_key: account
  user_secret_key: user
  private_key_secret_key: private_key
  private_key_passphrase_secret_key: private_key_passphrase
  role_secret_key: role
  warehouse_secret_key: warehouse
  database: FLEET_MVP_SIT
  schema: IDENTITY

writeback:
  staging_tables:
    CUSTOMER: IDENTITY.STG_CUSTOMER_MATCH_SCORE_WRITEBACK
    VEHICLE: IDENTITY.STG_VEHICLE_MATCH_SCORE_WRITEBACK
    DEVICE_VEHICLE: IDENTITY.STG_DEVICE_VEHICLE_MATCH_SCORE_WRITEBACK
    ACCOUNT_CUSTOMER: IDENTITY.STG_ACCOUNT_CUSTOMER_MATCH_SCORE_WRITEBACK
  merge_procedure: IDENTITY.MERGE_MATCH_SCORE_WRITEBACK
  decision_procedure: IDENTITY.APPLY_MATCH_DECISION_POLICY
```

Preferred auth is key-pair auth. If the environment requires username/password for a short-lived SIT setup, keep it in Databricks secrets and document the expiry date.

## Step 4: Create Databricks Secrets

Create the secret scope:

```bash
databricks secrets create-scope fleet-snowflake
```

Add the required secrets:

```bash
databricks secrets put-secret fleet-snowflake account
databricks secrets put-secret fleet-snowflake user
databricks secrets put-secret fleet-snowflake private_key
databricks secrets put-secret fleet-snowflake private_key_passphrase
databricks secrets put-secret fleet-snowflake role
databricks secrets put-secret fleet-snowflake warehouse
```

The Snowflake role should have only the permissions needed for candidate scoring:

```sql
GRANT USAGE ON DATABASE FLEET_MVP_SIT TO ROLE <role>;
GRANT USAGE ON SCHEMA FLEET_MVP_SIT.IDENTITY TO ROLE <role>;
GRANT SELECT ON TABLES IN SCHEMA FLEET_MVP_SIT.IDENTITY TO ROLE <role>;
GRANT INSERT, UPDATE, DELETE ON TABLES IN SCHEMA FLEET_MVP_SIT.IDENTITY TO ROLE <role>;
GRANT USAGE ON WAREHOUSE <warehouse> TO ROLE <role>;
```

Also grant procedure execution if the procedures are protected separately:

```sql
GRANT USAGE ON PROCEDURE FLEET_MVP_SIT.IDENTITY.MERGE_MATCH_SCORE_WRITEBACK(VARCHAR) TO ROLE <role>;
GRANT USAGE ON PROCEDURE FLEET_MVP_SIT.IDENTITY.APPLY_MATCH_DECISION_POLICY(VARCHAR) TO ROLE <role>;
```

## Step 5: Update Notebook Parameter Handling

Update `databricks/notebooks/candidate_match_scoring.py` to read Databricks widgets:

```python
dbutils.widgets.text("snowflake_secret_scope", "fleet-snowflake")
dbutils.widgets.text("snowflake_database", "FLEET_MVP_SIT")
dbutils.widgets.text("snowflake_schema", "IDENTITY")

secret_scope = dbutils.widgets.get("snowflake_secret_scope")
snowflake_database = dbutils.widgets.get("snowflake_database")
snowflake_schema = dbutils.widgets.get("snowflake_schema")
```

Build Snowflake connector options from secrets:

```python
sf_options = {
    "sfURL": dbutils.secrets.get(secret_scope, "account"),
    "sfUser": dbutils.secrets.get(secret_scope, "user"),
    "pem_private_key": dbutils.secrets.get(secret_scope, "private_key"),
    "sfRole": dbutils.secrets.get(secret_scope, "role"),
    "sfWarehouse": dbutils.secrets.get(secret_scope, "warehouse"),
    "sfDatabase": snowflake_database,
    "sfSchema": snowflake_schema,
}
```

If the private key is encrypted, include the passphrase according to the connector version supported by the runtime.

## Step 6: Write Scores to Snowflake Staging Tables

The notebook should continue to write score rows only to staging tables:

```text
IDENTITY.STG_CUSTOMER_MATCH_SCORE_WRITEBACK
IDENTITY.STG_VEHICLE_MATCH_SCORE_WRITEBACK
IDENTITY.STG_DEVICE_VEHICLE_MATCH_SCORE_WRITEBACK
IDENTITY.STG_ACCOUNT_CUSTOMER_MATCH_SCORE_WRITEBACK
```

The required score contract is:

```text
CANDIDATE_PAIR_ID
ENTITY_TYPE
MATCH_SCORE
RECOMMENDED_DECISION
REASON_CODES
MODEL_NAME
MODEL_VERSION
MLFLOW_RUN_ID
SCORING_RUN_ID
FEATURE_SNAPSHOT_ID
SCORED_AT
WRITEBACK_BATCH_ID
```

Use the same value for `SCORING_RUN_ID` and `WRITEBACK_BATCH_ID` for the baseline implementation unless there is a separate batch orchestration ID.

## Step 7: Call Snowflake Merge Procedure

After all staging writes complete, call:

```sql
CALL IDENTITY.MERGE_MATCH_SCORE_WRITEBACK('<writeback_batch_id>');
```

From Spark, use the Snowflake connector query path:

```python
def call_snowflake_procedure(spark, sf_options: dict[str, str], sql: str) -> None:
    (
        spark.read.format("snowflake")
        .options(**sf_options)
        .option("query", sql)
        .load()
        .collect()
    )


call_snowflake_procedure(
    spark,
    sf_options,
    f"CALL IDENTITY.MERGE_MATCH_SCORE_WRITEBACK('{scoring_run_id}')",
)
```

The merge key is:

```text
CANDIDATE_PAIR_ID
ENTITY_TYPE
MODEL_VERSION
SCORING_RUN_ID
```

This keeps score writeback idempotent for retries of the same run.

## Step 8: Call Snowflake Decision Procedure

After score merge succeeds, call:

```sql
CALL IDENTITY.APPLY_MATCH_DECISION_POLICY('<audit_run_id>');
```

Use the scoring run ID as the audit run ID for the baseline path:

```python
call_snowflake_procedure(
    spark,
    sf_options,
    f"CALL IDENTITY.APPLY_MATCH_DECISION_POLICY('{scoring_run_id}')",
)
```

This procedure materializes final decisions into:

```text
IDENTITY.CUSTOMER_MATCH_DECISION
IDENTITY.VEHICLE_MATCH_DECISION
IDENTITY.DEVICE_VEHICLE_MATCH_DECISION
IDENTITY.ACCOUNT_CUSTOMER_MATCH_DECISION
```

Review-band rows are inserted into:

```text
IDENTITY.MATCH_REVIEW_QUEUE
```

## Step 9: Validate Graph Eligibility

Validate that graph-eligible rows are exposed only through:

```text
IDENTITY.GRAPH_ELIGIBLE_MATCH_DECISION
```

Run:

```sql
SELECT
  ENTITY_TYPE,
  FINAL_DECISION,
  DECISION_STATUS,
  GRAPH_APPLY_STATUS,
  COUNT(*) AS ROW_COUNT
FROM IDENTITY.GRAPH_ELIGIBLE_MATCH_DECISION
GROUP BY 1, 2, 3, 4;
```

Expected controls:

```text
FINAL_DECISION = MATCH
DECISION_STATUS in AUTO_APPROVED, HUMAN_APPROVED
GRAPH_APPLY_STATUS = READY_TO_APPLY
IS_CURRENT = TRUE
```

No raw Databricks score table should be consumed by graph, xref, golden, or relationship logic.

## Step 10: Deploy and Run the Bundle

Validate the bundle:

```bash
databricks bundle validate -t dev
```

Deploy:

```bash
databricks bundle deploy -t dev
```

Run:

```bash
databricks bundle run candidate_matching_score_writeback -t dev
```

Capture the run ID, scoring run ID, MLflow run ID, and writeback batch ID in the implementation notes for the release.

## Step 11: Smoke Test in Snowflake

Run these checks after a successful job:

```sql
SELECT COUNT(*) FROM IDENTITY.CUSTOMER_MATCH_SCORE;
SELECT COUNT(*) FROM IDENTITY.VEHICLE_MATCH_SCORE;
SELECT COUNT(*) FROM IDENTITY.DEVICE_VEHICLE_MATCH_SCORE;
SELECT COUNT(*) FROM IDENTITY.ACCOUNT_CUSTOMER_MATCH_SCORE;

SELECT ENTITY_TYPE, FINAL_DECISION, DECISION_STATUS, COUNT(*)
FROM IDENTITY.CUSTOMER_MATCH_DECISION
GROUP BY 1, 2, 3;

SELECT REVIEW_STATUS, COUNT(*)
FROM IDENTITY.MATCH_REVIEW_QUEUE
GROUP BY 1;
```

Check audit fields:

```sql
SELECT
  SCORING_RUN_ID,
  MODEL_NAME,
  MODEL_VERSION,
  MLFLOW_RUN_ID,
  FEATURE_SNAPSHOT_ID,
  WRITEBACK_BATCH_ID
FROM IDENTITY.CUSTOMER_MATCH_SCORE
ORDER BY SCORED_AT DESC
LIMIT 20;
```

## Step 12: Required Review Before Promotion

Before promoting beyond SIT or dev:

- Confirm connector authentication uses secrets only.
- Confirm the Snowflake role cannot update golden or graph tables directly from Databricks.
- Confirm all score rows include `MODEL_VERSION`, `MLFLOW_RUN_ID`, `SCORING_RUN_ID`, and `WRITEBACK_BATCH_ID`.
- Confirm threshold policy version is stored on every decision row.
- Confirm review-band rows do not appear in `IDENTITY.GRAPH_ELIGIBLE_MATCH_DECISION`.
- Confirm rerunning the same writeback batch does not duplicate score rows.

## Done Criteria

This build step is complete when:

- The Databricks bundle validates.
- The Databricks job runs successfully in dev or SIT.
- Score rows are written to Snowflake staging tables.
- `IDENTITY.MERGE_MATCH_SCORE_WRITEBACK` merges scores into target score tables.
- `IDENTITY.APPLY_MATCH_DECISION_POLICY` creates governed decision rows.
- Review-band decisions appear in `IDENTITY.MATCH_REVIEW_QUEUE`.
- Only approved `MATCH` decisions appear in `IDENTITY.GRAPH_ELIGIBLE_MATCH_DECISION`.

