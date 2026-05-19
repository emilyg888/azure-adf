# SPEC.md — Partial Phase 4: LLM-Generated Transformation Code for One Dataset

## 1. Phase objective

Introduce a controlled LLM coding agent workflow for one sample dataset.

The agent will generate or refactor transformation code, tests and documentation from a structured transformation contract.

This is a partial Phase 4 implementation. It proves the agent-assisted delivery pattern without allowing the LLM to operate in production runtime.

---

## 2. Phase scope

### In scope

- Define LLM coding agent responsibilities
- Define agent input contract
- Define agent prompt templates
- Generate PySpark transformation code for one dataset
- Generate unit tests for one dataset
- Generate mapping documentation for one dataset
- Store generated assets in repo
- Register agent task metadata
- Register generated code asset metadata
- Require human review before use
- Create review checklist

### Out of scope

- Autonomous production deployment
- Runtime LLM transformation decisions
- Agent access to secrets
- Agent self-approval
- Multi-dataset generation
- Full CI/CD automation
- Automatic PR creation, unless available in the development environment
- Production governance approval workflow

---

## 3. Core design principle

```text
LLM agent generates code at build time.
Approved deterministic code runs at runtime.
```

The LLM agent must not be part of the production data execution path.

---

## 4. Agent responsibilities

### 4.1 Allowed

The agent may:

- read dataset contract
- read schema mapping
- read transformation rules
- generate PySpark transformation module
- generate notebook driver draft
- generate unit tests
- generate data test suggestions
- generate mapping documentation
- generate code review summary
- suggest DQ rules
- suggest lineage metadata

### 4.2 Not allowed

The agent must not:

- deploy directly to production
- approve its own output
- call production pipelines
- access secrets
- write production data
- alter production metadata directly
- override DQ failures
- make non-deterministic runtime transformation decisions

---

## 5. Metadata DDL

### 5.1 `md_coding_agent_task`

```sql
CREATE TABLE md_coding_agent_task (
    agent_task_id           STRING,
    dataset_id              STRING,
    task_type               STRING,
    input_contract_path     STRING,
    output_repo_path        STRING,
    target_language         STRING,
    target_runtime          STRING,
    status                  STRING,
    reviewer                STRING,
    created_at              TIMESTAMP,
    approved_at             TIMESTAMP
);
```

### 5.2 `md_generated_code_asset`

```sql
CREATE TABLE md_generated_code_asset (
    asset_id                STRING,
    agent_task_id           STRING,
    dataset_id              STRING,
    asset_type              STRING,
    repo_path               STRING,
    code_hash               STRING,
    model_used              STRING,
    prompt_version          STRING,
    review_status           STRING,
    active_flag             BOOLEAN
);
```

---

## 6. Agent task lifecycle

```text
Draft task
    ↓
Load input contract
    ↓
Generate code/tests/docs
    ↓
Write generated assets to repo branch or generated_assets folder
    ↓
Register generated assets
    ↓
Run local/unit tests
    ↓
Create review summary
    ↓
Human review
    ↓
Approved or rejected
    ↓
Approved code can be wired into transformation registry
```

---

## 7. Agent input contract

The agent should receive a structured contract.

Example:

```yaml
agent_task_id: AGT_POP_001
task_type: generate_transform
dataset_id: DS_REF_POPULATION_001
target_language: pyspark
target_runtime: fabric_spark_or_databricks

input_contract_path: metadata/contracts/population_by_age_contract.yaml

expected_outputs:
  - transforms/pyspark/population_by_age_transform.py
  - tests/unit/test_population_by_age_transform.py
  - docs/mappings/population_by_age_mapping.md

constraints:
  - no hardcoded storage account names
  - no secrets
  - no runtime LLM calls
  - transformation must be deterministic
  - code must expose transform_population_by_age function
  - output schema must match contract
```

---

## 8. Prompt templates

Create prompt files under:

```text
agent/prompts/
```

### 8.1 `generate_transform.md`

```markdown
# Role

You are a senior Azure/Fabric and PySpark data engineer.

# Task

Generate deterministic PySpark transformation code from the supplied dataset contract.

# Requirements

- Use PySpark DataFrame APIs unless SQL is explicitly required.
- Do not hardcode storage account names or environment-specific paths.
- Do not include secrets.
- Do not call an LLM at runtime.
- Expose a function with the required signature.
- Validate required input columns.
- Return a DataFrame.
- Keep code modular and testable.

# Input

{{DATASET_CONTRACT}}

# Output

Return only the Python module content.
```

### 8.2 `generate_tests.md`

```markdown
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
```

### 8.3 `generate_mapping_doc.md`

```markdown
# Role

You are a data modeller and data engineering documentation specialist.

# Task

Generate mapping documentation from the supplied transformation contract.

# Requirements

- Include source columns.
- Include target columns.
- Include transformation descriptions.
- Include data types.
- Include known assumptions.
- Include open questions.
- Do not invent missing mappings.

# Input

{{DATASET_CONTRACT}}

# Output

Return Markdown documentation.
```

### 8.4 `review_generated_code.md`

```markdown
# Role

You are a senior data engineering code reviewer.

# Task

Review generated transformation code against the dataset contract.

# Review areas

- Contract completeness
- Source column handling
- Target schema correctness
- Deterministic logic
- Error handling
- Test coverage
- Hardcoded environment values
- Secret leakage
- Runtime LLM dependency

# Input

Dataset contract:
{{DATASET_CONTRACT}}

Generated code:
{{GENERATED_CODE}}

Generated tests:
{{GENERATED_TESTS}}

# Output

Produce a concise review summary with risks and required fixes.
```

---

## 9. Generated artefacts

For the population dataset, the partial Phase 4 implementation should generate:

```text
transforms/pyspark/population_by_age_transform.py
tests/unit/test_population_by_age_transform.py
docs/mappings/population_by_age_mapping.md
agent/generated_assets/AGT_POP_001/review_summary.md
```

---

## 10. Review checklist

Create:

```text
agent/review_checklists/generated_transform_review.md
```

Checklist:

```markdown
# Generated transformation review checklist

## Contract alignment

- [ ] Dataset id matches contract
- [ ] Input columns are handled correctly
- [ ] Target columns match contract
- [ ] Data types are respected
- [ ] Required lookup joins are implemented

## Code quality

- [ ] No hardcoded storage account names
- [ ] No secrets
- [ ] No environment-specific paths
- [ ] Function is modular and testable
- [ ] Error handling is clear
- [ ] No runtime LLM calls

## Testing

- [ ] Unit tests exist
- [ ] Schema test exists
- [ ] Key transformation tests exist
- [ ] Invalid input tests exist
- [ ] Tests use synthetic/sample data only

## Governance

- [ ] PII handling reviewed if applicable
- [ ] DQ suggestions reviewed if applicable
- [ ] Lineage impact understood
- [ ] Human reviewer assigned

## Approval

- [ ] Approved
- [ ] Rejected
- [ ] Requires changes
```

---

## 11. Agent-generated code quality rules

The generated transformation code must:

- use explicit imports
- expose a single main transformation function
- include docstring
- validate required columns
- avoid hardcoded paths
- avoid pipeline-specific parameters
- avoid secrets
- avoid runtime LLM calls
- be deterministic
- be unit testable
- return a DataFrame

---

## 12. Human approval model

Human review is required before the generated code is used by the runtime pipeline.

Reviewer should check:

- transformation intent
- business meaning
- mapping correctness
- join logic
- data type handling
- null handling
- output schema
- test adequacy
- governance impact

Approval states:

```text
drafted
generated
under_review
approved
rejected
requires_changes
retired
```

---

## 13. Agent metadata examples

### 13.1 `md_coding_agent_task`

```yaml
agent_task_id: AGT_POP_001
dataset_id: DS_REF_POPULATION_001
task_type: generate_transform
input_contract_path: metadata/contracts/population_by_age_contract.yaml
output_repo_path: transforms/pyspark/population_by_age_transform.py
target_language: pyspark
target_runtime: fabric_spark
status: under_review
reviewer: data_engineer
created_at: 2026-05-19T10:00:00
approved_at:
```

### 13.2 `md_generated_code_asset`

```yaml
asset_id: AST_POP_TRANSFORM_001
agent_task_id: AGT_POP_001
dataset_id: DS_REF_POPULATION_001
asset_type: transform_module
repo_path: transforms/pyspark/population_by_age_transform.py
code_hash: pending
model_used: configured_llm
prompt_version: v0.1
review_status: under_review
active_flag: false
```

---

## 14. Acceptance criteria

Partial Phase 4 is complete when:

- agent prompt templates exist
- one agent task is defined for the sample dataset
- generated transformation module exists
- generated unit test file exists
- generated mapping documentation exists
- generated asset metadata is captured
- human review checklist exists
- generated code is not automatically deployed
- generated code can be approved or rejected

---

## 15. Test scenarios

| Scenario | Expected result |
|---|---|
| Valid contract supplied | agent generates transformation code |
| Contract missing required columns | agent flags missing information |
| Generated code contains hardcoded path | review fails |
| Generated code has runtime LLM call | review fails |
| Generated tests do not cover schema | review requires changes |
| Human approves code | asset status becomes approved |
| Human rejects code | asset status becomes rejected |

---

## 16. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Agent hallucinates transformation logic | Use structured contract and review |
| Agent generates plausible but wrong code | Require unit tests and human approval |
| Agent bypasses governance | Restrict agent to build-time only |
| Generated tests are weak | Review test coverage explicitly |
| Generated code differs from Erwin mapping | Check against schema mapping |
| Review burden becomes high | Agent generates review summary |
