resource "snowflake_database" "fleet" {
  count = var.manage_snowflake_foundation_objects ? 1 : 0

  name = local.snowflake_database_name

  lifecycle {
    prevent_destroy = true
  }
}

resource "snowflake_schema" "identity" {
  count = var.manage_snowflake_foundation_objects ? 1 : 0

  database = local.snowflake_database_name
  name     = var.snowflake_identity_schema

  depends_on = [snowflake_database.fleet]

  lifecycle {
    prevent_destroy = true
  }
}

resource "snowflake_warehouse" "connector" {
  count = var.manage_snowflake_foundation_objects ? 1 : 0

  name                = local.snowflake_warehouse_name
  warehouse_size      = var.snowflake_warehouse_size
  auto_suspend        = 60
  auto_resume         = true
  initially_suspended = true

  lifecycle {
    prevent_destroy = true
  }
}

resource "snowflake_account_role" "databricks_connector" {
  name = var.snowflake_connector_role
}

resource "snowflake_grant_account_role" "connector_role_to_user" {
  count = var.snowflake_connector_user == "" ? 0 : 1

  role_name = snowflake_account_role.databricks_connector.name

  user_name = var.snowflake_connector_user
}

resource "snowflake_grant_privileges_to_account_role" "warehouse_usage" {
  privileges        = ["USAGE"]
  account_role_name = snowflake_account_role.databricks_connector.name

  on_account_object {
    object_type = "WAREHOUSE"
    object_name = local.snowflake_warehouse_name
  }
}

resource "snowflake_grant_privileges_to_account_role" "database_usage" {
  privileges        = ["USAGE"]
  account_role_name = snowflake_account_role.databricks_connector.name

  on_account_object {
    object_type = "DATABASE"
    object_name = local.snowflake_database_name
  }
}

resource "snowflake_grant_privileges_to_account_role" "schema_usage" {
  privileges        = ["USAGE"]
  account_role_name = snowflake_account_role.databricks_connector.name

  on_schema {
    schema_name = local.snowflake_identity_schema_fqn
  }
}

resource "snowflake_grant_privileges_to_account_role" "existing_identity_tables_rw" {
  privileges        = ["SELECT", "INSERT", "UPDATE", "DELETE"]
  account_role_name = snowflake_account_role.databricks_connector.name

  on_schema_object {
    all {
      object_type_plural = "TABLES"
      in_schema          = local.snowflake_identity_schema_fqn
    }
  }
}

resource "snowflake_grant_privileges_to_account_role" "future_identity_tables_rw" {
  privileges        = ["SELECT", "INSERT", "UPDATE", "DELETE"]
  account_role_name = snowflake_account_role.databricks_connector.name

  on_schema_object {
    future {
      object_type_plural = "TABLES"
      in_schema          = local.snowflake_identity_schema_fqn
    }
  }
}

resource "snowflake_grant_privileges_to_account_role" "existing_identity_views_read" {
  privileges        = ["SELECT"]
  account_role_name = snowflake_account_role.databricks_connector.name

  on_schema_object {
    all {
      object_type_plural = "VIEWS"
      in_schema          = local.snowflake_identity_schema_fqn
    }
  }
}

resource "snowflake_grant_privileges_to_account_role" "future_identity_views_read" {
  privileges        = ["SELECT"]
  account_role_name = snowflake_account_role.databricks_connector.name

  on_schema_object {
    future {
      object_type_plural = "VIEWS"
      in_schema          = local.snowflake_identity_schema_fqn
    }
  }
}

resource "snowflake_grant_privileges_to_account_role" "existing_identity_procedures_usage" {
  privileges        = ["USAGE"]
  account_role_name = snowflake_account_role.databricks_connector.name

  on_schema_object {
    all {
      object_type_plural = "PROCEDURES"
      in_schema          = local.snowflake_identity_schema_fqn
    }
  }
}

resource "snowflake_grant_privileges_to_account_role" "future_identity_procedures_usage" {
  privileges        = ["USAGE"]
  account_role_name = snowflake_account_role.databricks_connector.name

  on_schema_object {
    future {
      object_type_plural = "PROCEDURES"
      in_schema          = local.snowflake_identity_schema_fqn
    }
  }
}

resource "terraform_data" "identity_resolution_ddl" {
  count = var.enable_snowflake_ddl_deploy ? 1 : 0

  input = filesha256("${path.module}/../../../metadata/ddl/fleet_customer360_identity_resolution.sql")

  provisioner "local-exec" {
    command = var.snowflake_cli_connection == "" ? "snow sql -f ${path.module}/../../../metadata/ddl/fleet_customer360_identity_resolution.sql" : "snow sql --connection ${var.snowflake_cli_connection} -f ${path.module}/../../../metadata/ddl/fleet_customer360_identity_resolution.sql"
  }
}
