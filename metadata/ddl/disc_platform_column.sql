CREATE TABLE IF NOT EXISTS disc_platform_column (
    discovery_run_id STRING,
    platform_name STRING,
    database_name STRING,
    schema_name STRING,
    object_name STRING,
    column_name STRING,
    data_type STRING,
    nullable_flag BOOLEAN,
    ordinal_position INT,
    sample_value STRING,
    discovered_at TIMESTAMP
);
