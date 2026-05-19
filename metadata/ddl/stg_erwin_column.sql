CREATE TABLE IF NOT EXISTS stg_erwin_column (
    model_version_id STRING,
    model_name STRING,
    erwin_model_version STRING,
    physical_object_name STRING,
    logical_attribute_name STRING,
    physical_column_name STRING,
    data_type STRING,
    length INT,
    precision_value INT,
    scale_value INT,
    nullable_flag BOOLEAN,
    primary_key_flag BOOLEAN,
    business_definition STRING,
    domain_name STRING,
    classification STRING
);
