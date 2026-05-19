CREATE TABLE IF NOT EXISTS stg_erwin_mapping (
    model_version_id STRING,
    model_name STRING,
    erwin_model_version STRING,
    source_system_name STRING,
    source_object_name STRING,
    source_column_name STRING,
    target_system_name STRING,
    target_object_name STRING,
    target_column_name STRING,
    transformation_text STRING,
    business_definition STRING,
    classification STRING
);
