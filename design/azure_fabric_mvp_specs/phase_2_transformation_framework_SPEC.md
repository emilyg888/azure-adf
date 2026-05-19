# SPEC.md — Phase 2: Transformation Framework MVP

## 1. Phase objective

Build the first reusable transformation framework that can execute deterministic transformation logic from a structured transformation contract.

The MVP should refactor the sample dataset transformation into a reusable pattern:

```text
metadata contract
    ↓
thin notebook driver
    ↓
transformation module
    ↓
target writer
    ↓
audit log
```

---

## 2. Phase scope

### In scope

- Create transformation contract format
- Create schema mapping metadata
- Create transformation rule metadata
- Create generic transformation notebook driver
- Create reusable transformation module for one sample dataset
- Create basic rule engine or transformation registry
- Create target writer interface
- Implement initial Delta/file target writer
- Create unit tests for sample transformation
- Create transformation audit logging

### Out of scope

- Full LLM agent generation workflow
- Full multi-target adapter library
- Snowflake / SQL / Cosmos production writes
- Full DQ engine
- Full PII masking
- Full source-to-target reconciliation QA
- Full CI/CD deployment

---

## 3. Functional requirements

### FR-001 — Transformation contract

The framework must support a structured transformation contract.

The contract must describe:

- dataset id
- input datasets
- lookup datasets
- output dataset
- source-to-target mappings
- transformation steps
- target write details
- required tests

---

### FR-002 — Generic notebook driver

The notebook driver must be generic and parameterised.

It must accept:

| Parameter | Purpose |
|---|---|
| environment | dev/test/prod |
| dataset_id | dataset to transform |
| run_id | pipeline run id |
| contract_path | optional override contract path |
| batch_date | logical batch date |

The notebook driver must:

```text
1. load environment config
2. load dataset metadata
3. load transformation contract
4. read input data
5. call transformation module or rule engine
6. write output through target writer
7. log audit result
```

---

### FR-003 — Transformation module

The transformation logic for the sample dataset must be implemented as a reusable Python/PySpark module.

Example location:

```text
transforms/pyspark/population_by_age_transform.py
```

The module should expose:

```python
def transform_population_by_age(df_population, df_country):
    return df_output
```

---

### FR-004 — Schema mapping metadata

The framework must capture source-to-target mapping.

Required fields:

- dataset id
- source column
- target column
- target data type
- nullable flag
- primary key flag
- business definition
- transformation rule id

---

### FR-005 — Transformation rule metadata

The framework must capture transformation steps.

Required fields:

- rule id
- dataset id
- rule name
- rule type
- source column
- target column
- rule expression
- rule sequence
- enabled flag

---

### FR-006 — Target writer

The framework must write transformation output through a target writer abstraction.

MVP target writer support:

- file target
- Delta target

Future target writer support:

- Snowflake
- Azure SQL
- Synapse SQL
- Cosmos DB

---

### FR-007 — Transformation audit

The framework must log:

- run id
- dataset id
- transformation start time
- transformation end time
- input row count
- output row count
- status
- error message
- code version
- contract version

---

## 4. Non-functional requirements

### NFR-001 — Deterministic execution

Given the same input and same transformation code, the same output should be produced.

### NFR-002 — No runtime LLM dependency

Transformation execution must not require an LLM call at runtime.

### NFR-003 — Testability

Transformation logic must be testable outside the full Fabric pipeline.

### NFR-004 — Reusability

The notebook driver must not be hardcoded to one dataset.

### NFR-005 — Extensibility

The target writer interface must support future platform adapters.

---

## 5. Metadata DDL

### 5.1 `md_schema_mapping`

```sql
CREATE TABLE md_schema_mapping (
    mapping_id              STRING,
    dataset_id              STRING,
    source_column           STRING,
    target_column           STRING,
    target_data_type        STRING,
    nullable_flag           BOOLEAN,
    primary_key_flag        BOOLEAN,
    business_definition     STRING,
    erwin_entity_name       STRING,
    erwin_attribute_name    STRING,
    transformation_rule_id  STRING,
    active_flag             BOOLEAN
);
```

### 5.2 `md_transformation_rule`

```sql
CREATE TABLE md_transformation_rule (
    rule_id                 STRING,
    dataset_id              STRING,
    rule_name               STRING,
    rule_type               STRING,
    source_column           STRING,
    target_column           STRING,
    rule_expression         STRING,
    rule_sequence           INT,
    enabled_flag            BOOLEAN
);
```

### 5.3 Extend `md_pipeline_audit_log`

Add or use:

```text
code_version
metadata_version
contract_version
```

If the current audit table does not include `contract_version`, add it later or capture in an extension table.

---

## 6. Transformation contract example

Create:

```text
metadata/contracts/population_by_age_contract.yaml
```

Example:

```yaml
dataset_id: DS_REF_POPULATION_001
dataset_name: population_by_age
contract_version: "0.1"

inputs:
  - name: raw_population
    role: primary
    format: csv
    delimiter: tab
    path: /raw/population

lookups:
  - name: dim_country
    format: csv
    delimiter: comma
    path: /lookup/dim_country
    join_key:
      source: country_code
      lookup: country_code_2_digit

target:
  platform: Delta
  storage_type: table
  format: delta
  schema: silver
  object: population_by_age
  path: /processed/population_by_age
  write_mode: overwrite
  write_strategy: full_load

mappings:
  - source_column: indic_de_geo_time
    target_column: country_code
    target_data_type: string
    nullable: false
    transformation_rule: extract second element after splitting by comma

  - source_column: indic_de_geo_time
    target_column: age_group
    target_data_type: string
    nullable: false
    transformation_rule: extract first element after splitting by comma and remove PC_ prefix

  - source_column: "2019"
    target_column: percentage_2019
    target_data_type: decimal(4,2)
    nullable: true
    transformation_rule: remove alphabetic characters and cast to decimal

transformations:
  - sequence: 10
    name: extract_age_group
    type: derive_column

  - sequence: 20
    name: extract_country_code
    type: derive_column

  - sequence: 30
    name: clean_percentage
    type: regex_clean_cast

  - sequence: 40
    name: pivot_age_group
    type: pivot

  - sequence: 50
    name: join_country_lookup
    type: join

tests:
  required:
    - schema_validation
    - country_code_not_null
    - output_row_count_greater_than_zero
    - expected_age_group_columns_present
```

---

## 7. Transformation module design

### 7.1 File

```text
transforms/pyspark/population_by_age_transform.py
```

### 7.2 Function signature

```python
from pyspark.sql import DataFrame

def transform_population_by_age(
    df_population: DataFrame,
    df_country: DataFrame
) -> DataFrame:
    """
    Transform raw population-by-age input into curated country age-band output.
    """
```

### 7.3 Expected transformation logic

```text
1. Split source composite field into age group and country code
2. Remove PC_ prefix from age group
3. Select country code, age group and 2019 percentage
4. Filter to valid two-character country codes
5. Remove alphabetic suffixes from percentage
6. Cast percentage to decimal
7. Pivot age groups into columns
8. Join country lookup
9. Rename target columns
10. Return curated DataFrame
```

### 7.4 Expected output columns

```text
country
country_code_2_digit
country_code_3_digit
population
age_group_0_14
age_group_15_24
age_group_25_49
age_group_50_64
age_group_65_79
age_group_80_max
```

---

## 8. Notebook driver design

### 8.1 File

```text
fabric/notebooks/generic_transform_driver.py
```

### 8.2 Pseudo-code

```python
dataset_id = get_param("dataset_id")
run_id = get_param("run_id")
environment = get_param("environment")

config = load_environment_config(environment)
contract = load_transformation_contract(dataset_id)

df_population = read_input(contract, name="raw_population")
df_country = read_lookup(contract, name="dim_country")

if dataset_id == "DS_REF_POPULATION_001":
    from transforms.pyspark.population_by_age_transform import transform_population_by_age
    df_output = transform_population_by_age(df_population, df_country)
else:
    df_output = execute_rule_engine(contract)

validate_output_schema(df_output, contract)
write_target(df_output, contract["target"])
write_transformation_audit(run_id, dataset_id, status="SUCCESS")
```

### 8.3 MVP note

The MVP may use a simple transformation registry:

```python
TRANSFORM_REGISTRY = {
    "DS_REF_POPULATION_001": transform_population_by_age
}
```

A full dynamic plugin registry can be introduced later.

---

## 9. Target writer design

### 9.1 Interface

```python
def write_target(df, target_contract):
    platform = target_contract["platform"].lower()

    if platform in ["delta", "lakehouse", "databricks"]:
        return write_delta(df, target_contract)

    if platform in ["adls", "onelake"]:
        return write_file(df, target_contract)

    raise ValueError(f"Unsupported MVP target platform: {platform}")
```

### 9.2 Delta writer

```python
def write_delta(df, target):
    (
        df.write
          .format("delta")
          .mode(target["write_mode"])
          .save(target["path"])
    )
```

### 9.3 File writer

```python
def write_file(df, target):
    (
        df.write
          .format(target["format"])
          .mode(target["write_mode"])
          .option("header", "true")
          .save(target["path"])
    )
```

---

## 10. Unit test design

### 10.1 Test file

```text
tests/unit/test_population_by_age_transform.py
```

### 10.2 Required tests

| Test | Expected result |
|---|---|
| test_output_schema | expected columns are present |
| test_country_code_extraction | country code is derived correctly |
| test_age_group_extraction | PC_ prefix is removed |
| test_percentage_cleaning | alphabetic suffixes removed |
| test_pivot_columns | age group columns are created |
| test_country_join | country lookup enriches output |
| test_no_invalid_country_codes | invalid country code rows excluded |

### 10.3 Sample test structure

```python
def test_output_schema(spark):
    df_population = create_sample_population_df(spark)
    df_country = create_sample_country_df(spark)

    df_output = transform_population_by_age(df_population, df_country)

    expected_columns = {
        "country",
        "country_code_2_digit",
        "country_code_3_digit",
        "population",
        "age_group_0_14",
        "age_group_15_24",
        "age_group_25_49",
        "age_group_50_64",
        "age_group_65_79",
        "age_group_80_max"
    }

    assert expected_columns.issubset(set(df_output.columns))
```

---

## 11. Acceptance criteria

Phase 2 is complete when:

- transformation contract exists for the sample dataset
- schema mapping metadata exists
- transformation rule metadata exists
- generic transformation notebook driver exists
- sample transformation logic is refactored into a reusable module
- target writer interface exists
- Delta or file target writer works
- unit tests exist for sample transformation
- transformation audit is captured
- output matches expected sample result

---

## 12. Test scenarios

| Scenario | Expected result |
|---|---|
| Valid source and lookup data | transformation succeeds |
| Missing lookup data | transformation fails with clear error |
| Missing required source column | schema validation fails |
| Invalid percentage value | value is cleaned or rejected based on rule |
| Empty input | warning or failure based on config |
| Unsupported target | target writer raises clear error |
| Output schema mismatch | validation fails |

---

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Rule engine becomes too complex too early | Use registry + module pattern first |
| Transformation logic stays embedded in notebook | Enforce module extraction |
| Target writer over-generalised | Implement only Delta/file in MVP |
| Tests too weak | Require schema, row count and key transformation tests |
| Contract and code drift | Capture contract version and code version in audit |
