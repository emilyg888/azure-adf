CREATE TABLE IF NOT EXISTS stg_erwin_model (
    model_version_id STRING,
    model_name STRING,
    erwin_model_version STRING,
    subject_area STRING,
    export_timestamp TIMESTAMP,
    exported_by STRING,
    import_status STRING,
    imported_at TIMESTAMP
);
