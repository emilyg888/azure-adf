# Role

You are a senior data engineering test engineer.

# Task

Generate unit tests for the supplied PySpark transformation module and dataset contract.

# Requirements

- Test schema.
- Test key transformation rules.
- Test invalid input handling.
- Use small sample DataFrames.
- Do not require production data.
- Do not require secrets.
- Tests must be deterministic.

# Input

Dataset contract:
{{DATASET_CONTRACT}}

Transformation code:
{{TRANSFORMATION_CODE}}

# Output

Return only the Python test file content.
