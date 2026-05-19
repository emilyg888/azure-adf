CREATE TABLE IF NOT EXISTS md_dataset (
    dataset_id STRING,
    dataset_name STRING,
    business_domain STRING,
    source_system_id STRING,
    data_owner STRING,
    data_steward STRING,
    sensitivity_class STRING,
    load_frequency STRING,
    load_type STRING,
    active_flag BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
