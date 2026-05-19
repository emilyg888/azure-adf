CREATE TABLE IF NOT EXISTS md_generated_code_asset (
    asset_id STRING,
    agent_task_id STRING,
    dataset_id STRING,
    asset_type STRING,
    repo_path STRING,
    code_hash STRING,
    model_used STRING,
    prompt_version STRING,
    review_status STRING,
    active_flag BOOLEAN
);
