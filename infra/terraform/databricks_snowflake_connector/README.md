# Databricks Snowflake Connector IaC

This Terraform package captures the durable infrastructure and access controls around the Databricks-to-Snowflake candidate matching path.

It complements, rather than replaces, the Databricks Asset Bundle under:

```text
databricks/bundles/candidate_matching
```

## Ownership Boundary

Terraform owns:

- Databricks secret scope metadata for Snowflake connector credentials.
- Databricks secret scope ACLs.
- Databricks all-purpose cluster policy enforcing 15-30 minute auto-termination.
- Databricks cluster policy usage permissions.
- Snowflake connector role and connector grants.
- Optionally, Snowflake database, schema, and warehouse creation when `manage_snowflake_foundation_objects = true`.
- Optional Snowflake DDL deployment hook through the local `snow` CLI.

Databricks Asset Bundles own:

- Candidate matching job definition.
- Notebook sync and job deployment.
- Job parameters.
- Serverless workflow execution.

Terraform does **not** own:

- Databricks secret values. These must not be written to Terraform state.
- MLflow run metadata.
- Candidate score rows, decision rows, review queue rows, or golden records.

## Files

```text
infra/terraform/databricks_snowflake_connector/
  README.md
  versions.tf
  providers.tf
  variables.tf
  databricks.tf
  snowflake.tf
  outputs.tf
  examples/dev.tfvars.example
```

## Prerequisites

- Terraform `>= 1.5.0`.
- Databricks CLI profile for the target workspace, for example `fleet-dev-active`.
- Snowflake Terraform provider credentials through a service user or admin user.
- The Snowflake admin private key supplied through a secure mechanism, such as:

```bash
export TF_VAR_snowflake_admin_private_key="$(cat ~/.snowflake/keys/iac_user_key_unencrypted.p8)"
```

Do not commit private keys, passphrases, Snowflake passwords, or Databricks secret values.

## Bootstrap

From repo root:

```bash
cd infra/terraform/databricks_snowflake_connector
cp examples/dev.tfvars.example dev.tfvars
```

Edit `dev.tfvars` with your Snowflake organization, account, and IaC user values.

Initialize:

```bash
terraform init
```

Validate:

```bash
terraform validate
```

Plan:

```bash
terraform plan -var-file=dev.tfvars
```

Apply:

```bash
terraform apply -var-file=dev.tfvars
```

## Import Existing Databricks Resources

These resources were created manually during the working deployment.

Secret scope:

```bash
terraform import \
  -var-file=dev.tfvars \
  databricks_secret_scope.snowflake \
  fleet-snowflake
```

Cluster policy:

```bash
terraform import \
  -var-file=dev.tfvars \
  databricks_cluster_policy.all_purpose_autotermination \
  000CA5E1329B3212
```

After importing, run:

```bash
terraform plan -var-file=dev.tfvars
```

If the imported cluster policy differs only by formatting, check the rendered `definition` carefully before applying.

## Snowflake Connector Role

The package creates a scoped role:

```text
FLEET_DATABRICKS_CONNECTOR_ROLE
```

It grants:

- `USAGE` on the connector warehouse.
- `USAGE` on the Fleet database.
- `USAGE` on the `IDENTITY` schema.
- `SELECT`, `INSERT`, `UPDATE`, and `DELETE` on existing and future identity tables.
- `SELECT` on existing and future identity views.
- `USAGE` on existing and future identity procedures.

Set `snowflake_connector_user` in `dev.tfvars` to grant this role to the Snowflake user stored in the Databricks `fleet-snowflake` secret scope.

After the role is granted and tested, update the Databricks secret:

```bash
databricks secrets put-secret fleet-snowflake role --profile fleet-dev-active
```

Use:

```text
FLEET_DATABRICKS_CONNECTOR_ROLE
```

## Existing Snowflake Objects

By default, this package does **not** manage the existing Snowflake database, schema, or warehouse:

```hcl
manage_snowflake_foundation_objects = false
```

This avoids accidental replacement of deployed objects such as:

```text
FLEET_MVP_SIT
FLEET_MVP_SIT.IDENTITY
FLEET_MVP_SIT_WH
```

If you already imported those foundation objects into Terraform state, remove only the Terraform state bindings:

```bash
terraform state rm snowflake_database.fleet
terraform state rm snowflake_schema.identity
terraform state rm snowflake_warehouse.connector
```

`terraform state rm` does not delete Snowflake objects. It only removes them from Terraform state.

Only set this to true in a new environment where Terraform should create the foundation objects:

```hcl
manage_snowflake_foundation_objects = true
```

## Optional DDL Deployment Hook

By default, Terraform does not deploy the Snowflake identity DDL:

```hcl
enable_snowflake_ddl_deploy = false
```

To let Terraform run the DDL through the local `snow` CLI:

```hcl
enable_snowflake_ddl_deploy = true
snowflake_cli_connection    = "fleet-dev"
```

This runs:

```text
metadata/ddl/fleet_customer360_identity_resolution.sql
```

Use this only from a controlled CI or admin workstation where `snow` is configured.

## Secret Values

Terraform intentionally creates only the Databricks secret scope and ACLs.

Populate values separately:

```bash
databricks secrets put-secret fleet-snowflake account --profile fleet-dev-active
databricks secrets put-secret fleet-snowflake user --profile fleet-dev-active
databricks secrets put-secret fleet-snowflake role --profile fleet-dev-active
databricks secrets put-secret fleet-snowflake warehouse --profile fleet-dev-active
databricks secrets put-secret fleet-snowflake private_key --profile fleet-dev-active
databricks secrets put-secret fleet-snowflake private_key_passphrase --profile fleet-dev-active
```

For the current serverless Snowflake connector path, `private_key` should be the one-line unencrypted PKCS8 key body that starts with `MII`.

Generate it from a local unencrypted key:

```bash
awk 'NF && !/-----/{printf "%s", $0}' ~/.snowflake/keys/snowflake_rsa_key_unencrypted.p8
```

## Validation After Apply

Databricks:

```bash
databricks cluster-policies list --profile fleet-dev-active
databricks secrets list-scopes --profile fleet-dev-active
databricks secrets list-secrets fleet-snowflake --profile fleet-dev-active
```

Snowflake:

```sql
USE ROLE FLEET_DATABRICKS_CONNECTOR_ROLE;
USE WAREHOUSE FLEET_MVP_SIT_WH;
USE DATABASE FLEET_MVP_SIT;
USE SCHEMA IDENTITY;

SELECT COUNT(*) FROM CUSTOMER_MATCH_CANDIDATE;
SHOW PROCEDURES LIKE 'MERGE_MATCH_SCORE_WRITEBACK';
SHOW PROCEDURES LIKE 'APPLY_MATCH_DECISION_POLICY';
```

Databricks bundle smoke test:

```bash
cd ../../../databricks/bundles/candidate_matching
databricks bundle validate -t dev --profile fleet-dev-active
databricks bundle run candidate_matching_score_writeback -t dev --profile fleet-dev-active
```
