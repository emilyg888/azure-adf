CREATE TABLE IF NOT EXISTS md_schema_mapping (
    mapping_id STRING,
    dataset_id STRING,
    source_column STRING,
    target_column STRING,
    target_data_type STRING,
    nullable_flag BOOLEAN,
    primary_key_flag BOOLEAN,
    business_definition STRING,
    erwin_entity_name STRING,
    erwin_attribute_name STRING,
    transformation_rule_id STRING,
    active_flag BOOLEAN
);
