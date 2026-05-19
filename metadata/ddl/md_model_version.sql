CREATE TABLE IF NOT EXISTS md_model_version (
    model_version_id STRING,
    model_name STRING,
    erwin_model_version STRING,
    export_timestamp TIMESTAMP,
    export_source STRING,
    imported_by STRING,
    import_status STRING,
    active_flag BOOLEAN
);
