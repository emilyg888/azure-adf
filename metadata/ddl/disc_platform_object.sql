CREATE TABLE IF NOT EXISTS disc_platform_object (
    discovery_run_id STRING,
    platform_name STRING,
    database_name STRING,
    schema_name STRING,
    object_name STRING,
    object_type STRING,
    object_path STRING,
    file_format STRING,
    discovered_at TIMESTAMP
);
