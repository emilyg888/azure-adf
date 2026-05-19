CREATE TABLE IF NOT EXISTS md_schema_mapping (
    schema_mapping_id STRING,
    dataset_id STRING,
    source_column STRING,
    target_column STRING,
    target_data_type STRING,
    nullable BOOLEAN
);
