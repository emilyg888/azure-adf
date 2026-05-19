CREATE TABLE IF NOT EXISTS md_coding_agent_task (
    task_id STRING,
    dataset_id STRING,
    task_type STRING,
    prompt_path STRING,
    status STRING,
    created_at TIMESTAMP
);
