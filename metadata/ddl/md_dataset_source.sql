CREATE TABLE IF NOT EXISTS md_dataset_source (
    dataset_source_id STRING,
    dataset_id STRING,
    source_object_type STRING,
    source_database STRING,
    source_schema STRING,
    source_object STRING,
    source_path STRING,
    source_format STRING,
    source_delimiter STRING,
    watermark_column STRING,
    incremental_filter STRING,
    active_flag BOOLEAN
);
