variable "databricks_profile" {
  description = "Databricks CLI profile for the target workspace."
  type        = string
  default     = "fleet-dev-active"
}

variable "databricks_snowflake_secret_scope" {
  description = "Databricks secret scope that stores Snowflake connector credentials. Secret values are managed outside Terraform."
  type        = string
  default     = "fleet-snowflake"
}

variable "databricks_secret_reader_group" {
  description = "Databricks group allowed to read Snowflake connector secrets. Use a narrow service/run group outside dev."
  type        = string
  default     = "users"
}

variable "databricks_cluster_policy_user_group" {
  description = "Databricks group allowed to use the all-purpose cluster auto-termination policy."
  type        = string
  default     = "users"
}

variable "cluster_policy_name" {
  description = "Name of the all-purpose cluster auto-termination policy."
  type        = string
  default     = "All-Purpose Auto-Termination 20m"
}

variable "snowflake_organization_name" {
  description = "Snowflake organization name for provider authentication."
  type        = string
}

variable "snowflake_account_name" {
  description = "Snowflake account name for provider authentication."
  type        = string
}

variable "snowflake_admin_user" {
  description = "Snowflake admin or IaC service user."
  type        = string
}

variable "snowflake_admin_role" {
  description = "Snowflake role used by Terraform to manage connector grants."
  type        = string
  default     = "ACCOUNTADMIN"
}

variable "snowflake_authenticator" {
  description = "Snowflake provider authenticator."
  type        = string
  default     = "SNOWFLAKE_JWT"
}

variable "snowflake_admin_private_key" {
  description = "Snowflake admin private key for Terraform provider authentication. Supply via TF_VAR_snowflake_admin_private_key or a secure CI secret."
  type        = string
  sensitive   = true
}

variable "snowflake_database" {
  description = "Snowflake database used by the Fleet SIT identity solution."
  type        = string
  default     = "FLEET_MVP_SIT"
}

variable "snowflake_identity_schema" {
  description = "Snowflake schema that contains candidate matching tables, scores, decisions, procedures, and review queue."
  type        = string
  default     = "IDENTITY"
}

variable "snowflake_warehouse" {
  description = "Snowflake warehouse used by Databricks connector jobs."
  type        = string
  default     = "FLEET_MVP_SIT_WH"
}

variable "snowflake_warehouse_size" {
  description = "Warehouse size to use when Terraform manages the connector warehouse."
  type        = string
  default     = "XSMALL"
}

variable "snowflake_connector_role" {
  description = "Scoped Snowflake role for Databricks candidate scoring read/writeback access."
  type        = string
  default     = "FLEET_DATABRICKS_CONNECTOR_ROLE"
}

variable "manage_snowflake_foundation_objects" {
  description = "When true, Terraform creates/manages the Snowflake database, identity schema, and warehouse. Keep false when adopting already-deployed objects."
  type        = bool
  default     = false
}

variable "snowflake_connector_user" {
  description = "Optional Snowflake user used by Databricks. When set, Terraform grants snowflake_connector_role to this user."
  type        = string
  default     = ""
}

variable "enable_snowflake_ddl_deploy" {
  description = "When true, Terraform runs the Snowflake identity DDL through the local snow CLI. Leave false unless snow CLI is configured in the execution environment."
  type        = bool
  default     = false
}

variable "snowflake_cli_connection" {
  description = "Optional snow CLI connection name used by the DDL deployment hook."
  type        = string
  default     = ""
}
