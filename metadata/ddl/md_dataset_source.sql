CREATE TABLE IF NOT EXISTS md_dataset_source (
    dataset_source_id STRING,
    dataset_id STRING,
    source_system_id STRING,
    source_object STRING,
    ingestion_mode STRING,
    is_active BOOLEAN
);
