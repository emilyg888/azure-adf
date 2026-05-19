CREATE TABLE IF NOT EXISTS md_pipeline_audit_log (
    run_id STRING,
    dataset_id STRING,
    pipeline_name STRING,
    activity_name STRING,
    status STRING,
    source_record_count BIGINT,
    target_record_count BIGINT,
    rejected_record_count BIGINT,
    warning_count BIGINT,
    error_message STRING,
    code_version STRING,
    metadata_version STRING,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
