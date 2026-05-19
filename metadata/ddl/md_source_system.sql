CREATE TABLE IF NOT EXISTS md_source_system (
    source_system_id STRING,
    source_system_name STRING,
    source_type STRING,
    connection_name STRING,
    auth_method STRING,
    owner STRING,
    active_flag BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
