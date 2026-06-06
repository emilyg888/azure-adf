locals {
  snowflake_database_name       = var.snowflake_database
  snowflake_identity_schema_fqn = "\"${var.snowflake_database}\".\"${var.snowflake_identity_schema}\""
  snowflake_warehouse_name      = var.snowflake_warehouse
}

