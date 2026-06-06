resource "databricks_secret_scope" "snowflake" {
  name = var.databricks_snowflake_secret_scope
}

resource "databricks_secret_acl" "snowflake_reader" {
  scope      = databricks_secret_scope.snowflake.name
  principal  = var.databricks_secret_reader_group
  permission = "READ"
}

resource "databricks_cluster_policy" "all_purpose_autotermination" {
  name        = var.cluster_policy_name
  description = "Requires all-purpose clusters to auto-terminate after 15-30 minutes of inactivity. Default is 20 minutes."

  definition = file("${path.module}/../../../databricks/cluster_policies/all_purpose_autotermination_20m.json")
}

resource "databricks_permissions" "all_purpose_autotermination_usage" {
  cluster_policy_id = databricks_cluster_policy.all_purpose_autotermination.id

  access_control {
    group_name       = var.databricks_cluster_policy_user_group
    permission_level = "CAN_USE"
  }
}
