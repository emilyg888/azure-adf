output "databricks_snowflake_secret_scope" {
  description = "Databricks secret scope name for Snowflake connector credentials."
  value       = databricks_secret_scope.snowflake.name
}

output "databricks_cluster_policy_id" {
  description = "Cluster policy ID enforcing all-purpose auto-termination."
  value       = databricks_cluster_policy.all_purpose_autotermination.id
}

output "snowflake_connector_role" {
  description = "Snowflake role granted connector privileges."
  value       = snowflake_account_role.databricks_connector.name
}

output "snowflake_identity_schema" {
  description = "Fully-qualified Snowflake identity schema."
  value       = local.snowflake_identity_schema_fqn
}

output "snowflake_connector_warehouse" {
  description = "Snowflake warehouse used by Databricks connector jobs."
  value       = local.snowflake_warehouse_name
}
