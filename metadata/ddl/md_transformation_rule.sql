CREATE TABLE IF NOT EXISTS md_transformation_rule (
    transformation_rule_id STRING,
    dataset_id STRING,
    rule_name STRING,
    rule_type STRING,
    rule_expression STRING,
    execution_order INT
);
