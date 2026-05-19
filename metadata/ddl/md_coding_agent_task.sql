CREATE TABLE IF NOT EXISTS md_coding_agent_task (
    agent_task_id STRING,
    dataset_id STRING,
    task_type STRING,
    input_contract_path STRING,
    output_repo_path STRING,
    target_language STRING,
    target_runtime STRING,
    status STRING,
    reviewer STRING,
    created_at TIMESTAMP,
    approved_at TIMESTAMP
);
