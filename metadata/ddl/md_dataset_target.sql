CREATE TABLE IF NOT EXISTS md_dataset_target (
    target_id STRING,
    dataset_id STRING,
    target_platform STRING,
    target_storage_type STRING,
    target_format STRING,
    target_connection_name STRING,
    target_database STRING,
    target_schema STRING,
    target_object STRING,
    target_path STRING,
    write_mode STRING,
    write_strategy STRING,
    partition_columns STRING,
    primary_key_columns STRING,
    watermark_column STRING,
    active_flag BOOLEAN
);
