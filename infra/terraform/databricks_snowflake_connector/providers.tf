provider "databricks" {
  profile = var.databricks_profile
}

provider "snowflake" {
  organization_name = var.snowflake_organization_name
  account_name      = var.snowflake_account_name
  user              = var.snowflake_admin_user
  role              = var.snowflake_admin_role
  authenticator     = var.snowflake_authenticator
  private_key       = var.snowflake_admin_private_key
}

