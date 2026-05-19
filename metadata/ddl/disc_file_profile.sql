CREATE TABLE IF NOT EXISTS disc_file_profile (
    discovery_run_id STRING,
    dataset_id STRING,
    path STRING,
    file_format STRING,
    delimiter STRING,
    header_flag BOOLEAN,
    file_count BIGINT,
    total_size_bytes BIGINT,
    inferred_column_count INT,
    sample_row_count BIGINT,
    latest_modified_at TIMESTAMP,
    discovered_at TIMESTAMP
);
