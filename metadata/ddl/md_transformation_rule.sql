CREATE TABLE IF NOT EXISTS md_transformation_rule (
    rule_id STRING,
    dataset_id STRING,
    rule_name STRING,
    rule_type STRING,
    source_column STRING,
    target_column STRING,
    rule_expression STRING,
    rule_sequence INT,
    enabled_flag BOOLEAN
);
