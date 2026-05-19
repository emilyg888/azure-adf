CREATE TABLE IF NOT EXISTS md_pipeline_audit_log (
    audit_run_id STRING,
    pipeline_name STRING,
    dataset_id STRING,
    status STRING,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    message STRING
);
