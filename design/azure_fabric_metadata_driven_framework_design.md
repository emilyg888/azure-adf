# Metadata-Driven Azure/Fabric Data Ingestion & Transformation Framework

## 1. Document purpose

This document defines a reusable design scaffold for an Azure/Fabric-based data ingestion and transformation framework.

The framework is intended to support data movement and transformation across platforms such as:

- Azure Synapse
- ADLS Gen2
- Microsoft Fabric OneLake / Lakehouse
- Azure Databricks Delta Lake
- Snowflake
- Azure SQL Database
- Synapse Dedicated SQL Pool
- Cosmos DB
- Other future target platforms through pluggable target adapters

The framework is designed to be:

- metadata-driven
- reusable across datasets
- compatible with Quest Erwin as the data modelling authority
- capable of using Python/PySpark notebooks for transformation logic
- extensible for data governance controls, including data quality, lineage, PII masking and certification
- ready for LLM coding agent assistance
- ready for Azure DevOps CI/CD integration in later phases

---

## 2. Executive summary

The proposed framework separates orchestration, metadata, generated code, transformation execution and governance controls.

The core principle is:

> Fabric orchestrates.  
> Metadata decides.  
> The LLM coding agent accelerates build-time code generation.  
> Notebooks and target adapters execute deterministic approved logic.  
> Governance validates and certifies.

The framework should not be built as a collection of one-off pipelines. Instead, it should use a generic pipeline pattern where dataset-specific behaviour is driven by metadata and contracts.

---

## 3. Key design principles

### 3.1 Metadata over hardcoding

Dataset-specific configuration should be externalised into metadata.

Avoid hardcoding:

- source paths
- target paths
- table names
- file formats
- transformation rules
- DQ rules
- write modes
- primary keys
- partition columns
- PII classifications

The pipeline should read metadata and execute the correct behaviour.

---

### 3.2 Fabric pipeline as orchestration layer

Fabric pipeline activities should be used to orchestrate ingestion, transformation, governance and audit steps.

However, a Fabric activity is not always the compute engine.

Recommended distinction:

| Layer | Responsibility |
|---|---|
| Fabric Pipeline | Orchestration, dependency management, parameter passing, monitoring |
| Copy Activity | Data movement / ingestion compute |
| Fabric Notebook | Spark-based transformation / validation compute |
| Databricks Job / Notebook | Databricks-based transformation compute |
| SQL procedure / script | Warehouse-native ELT compute |
| Snowflake warehouse | Snowflake-native transformation or load compute |
| Cosmos DB connector / SDK | Document write / upsert execution |
| Azure DevOps | Build, test, approval and deployment control plane |

---

### 3.3 LLM coding agent is build-time only

The LLM coding agent should generate transformation code, tests, documentation and mapping artefacts.

It should not make runtime transformation decisions in production.

Recommended rule:

> The LLM agent writes code.  
> Automation tests code.  
> Humans approve material changes.  
> Pipelines execute approved deterministic artefacts only.

Avoid this pattern:

```text
Runtime pipeline → calls LLM → LLM decides transformation logic → writes production data
```

Use this pattern instead:

```text
Metadata contract → LLM coding agent → generated code → tests → review → approved release → runtime execution
```

---

### 3.4 Human-in-the-loop for material changes

Human approval should be risk-based.

Mandatory human review should apply when changes affect:

- business transformation logic
- PII handling
- masking rules
- regulatory fields
- financial reporting data
- deduplication rules
- primary keys
- joins
- SCD logic
- target schemas
- certified data products
- data quality thresholds
- lineage mappings

Low-risk documentation or boilerplate changes may be approved through automated gates if policies allow.

---

### 3.5 Governance by design

Governance should be designed as pluggable control gates, not added later as documentation.

Governance controls should be inserted at defined points:

```text
Before ingestion
After raw landing
Before transformation
Before curated write
Before publication
After pipeline completion
```

---

### 3.6 Target adapter pattern

Targets should not be treated as only file formats.

The framework must support platform-specific target contracts.

Examples:

- Delta table
- Parquet file
- Snowflake table
- Azure SQL table
- Synapse SQL table
- Cosmos DB container
- JSON document collection
- future API or streaming sink

The framework should support a generic target writer interface with target-specific adapters.

---

## 4. High-level architecture

```text
┌──────────────────────────────────────────────────────────────────────┐
│                         Design & Metadata Layer                       │
│                                                                      │
│  Quest Erwin          Mapping Specs          Governance Rules         │
│  Logical Model        Target Contracts       DQ / PII / Lineage       │
└───────────────┬─────────────────────┬─────────────────────┬────────┘
                │                     │                     │
                ▼                     ▼                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         Metadata Repository                           │
│                                                                      │
│  md_dataset             md_source_system       md_dataset_target      │
│  md_schema_mapping      md_transform_rule      md_governance_rule     │
│  md_agent_task          md_generated_asset     md_audit_log           │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       LLM Coding Agent Layer                          │
│                                                                      │
│  Generate PySpark / SQL / dbt / Python transformation code             │
│  Generate unit tests, data tests, documentation and mapping summaries  │
│  Raise pull request for review                                        │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Engineering & Release Control Plane                 │
│                                                                      │
│  Git Repo        Pull Request        CI Tests        Approval Gate     │
│  Azure DevOps    Versioning          Evidence Pack   CD Deployment     │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         Runtime Orchestration Layer                    │
│                                                                      │
│  Fabric Pipeline                                                      │
│   ├── Lookup metadata                                                 │
│   ├── ForEach dataset                                                 │
│   ├── Copy Activity                                                   │
│   ├── Notebook / Databricks / SQL Activity                             │
│   ├── Governance Activity                                             │
│   └── Audit Activity                                                  │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         Data Platform Targets                         │
│                                                                      │
│  ADLS / OneLake / Lakehouse / Databricks Delta / Snowflake / SQL DB    │
│  Synapse SQL / Cosmos DB / Other target platforms                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 5. Runtime architecture

### 5.1 Generic pipeline flow

```text
pl_metadata_driven_data_pipeline
│
├── 1. Initialise run
│     ├── generate run_id
│     ├── load environment config
│     └── create audit record
│
├── 2. Lookup active datasets
│     └── filter by domain, schedule, dataset_group or manual trigger
│
├── 3. ForEach dataset
│     │
│     ├── 3.1 Load source metadata
│     ├── 3.2 Load target contract
│     ├── 3.3 Load schema mapping
│     ├── 3.4 Load transformation rules
│     ├── 3.5 Load governance rules
│     │
│     ├── 3.6 Ingest data
│     │     └── Copy Activity / source-specific extractor
│     │
│     ├── 3.7 Validate landing
│     │     └── row count, file presence, schema drift
│     │
│     ├── 3.8 Transform data
│     │     └── Fabric notebook / Databricks job / SQL procedure
│     │
│     ├── 3.9 Run governance controls
│     │     └── DQ, PII, lineage, certification checks
│     │
│     ├── 3.10 Write target
│     │     └── target adapter
│     │
│     └── 3.11 Log outcome
│           └── success, warning, failed, quarantined
│
└── 4. Finalise run
      ├── publish audit report
      ├── notify support channel
      └── update operational dashboard
```

---

## 6. Compute design

### 6.1 Ingestion compute

Use Fabric Copy Activity for simple extract-and-load patterns.

Examples:

| Source | Target | Compute |
|---|---|---|
| Synapse table | ADLS raw zone | Fabric Copy Activity |
| ADLS files | OneLake Lakehouse Files | Fabric Copy Activity |
| Blob files | ADLS / OneLake | Fabric Copy Activity |
| SQL DB table | Lakehouse bronze table | Fabric Copy Activity |
| Snowflake table | OneLake / ADLS | Copy Activity or Snowflake unload pattern |

### 6.2 Transformation compute

Use the appropriate compute engine based on workload.

| Workload | Recommended compute |
|---|---|
| Bronze to Silver PySpark transformations | Fabric Notebook |
| ADLS to Databricks Delta | Databricks Job / Notebook |
| Warehouse-native ELT | SQL procedure / script |
| Snowflake transformations | Snowflake warehouse |
| Simple business-led shaping | Dataflow Gen2 |
| Cosmos document shaping | Notebook / SDK / connector |

### 6.3 Governance compute

Governance checks can be executed through:

- Fabric notebooks
- Databricks notebooks
- SQL procedures
- Great Expectations / custom DQ framework
- Microsoft Purview API integration
- custom metadata service

---

## 7. Metadata model

### 7.1 `md_source_system`

Stores registered source systems.

```sql
CREATE TABLE md_source_system (
    source_system_id        STRING,
    source_system_name      STRING,
    source_type             STRING,
    connection_name         STRING,
    auth_method             STRING,
    owner                   STRING,
    active_flag             BOOLEAN,
    created_at              TIMESTAMP,
    updated_at              TIMESTAMP
);
```

Example source types:

- SynapseSQL
- AzureSQL
- ADLS
- Blob
- OneLake
- Snowflake
- CosmosDB
- API

---

### 7.2 `md_dataset`

Stores business dataset registration.

```sql
CREATE TABLE md_dataset (
    dataset_id              STRING,
    dataset_name            STRING,
    business_domain         STRING,
    source_system_id        STRING,
    data_owner              STRING,
    data_steward            STRING,
    sensitivity_class       STRING,
    load_frequency          STRING,
    load_type               STRING,
    active_flag             BOOLEAN,
    created_at              TIMESTAMP,
    updated_at              TIMESTAMP
);
```

---

### 7.3 `md_dataset_source`

Stores physical source details.

```sql
CREATE TABLE md_dataset_source (
    dataset_source_id       STRING,
    dataset_id              STRING,
    source_object_type      STRING,
    source_database         STRING,
    source_schema           STRING,
    source_object           STRING,
    source_path             STRING,
    source_format           STRING,
    source_delimiter        STRING,
    watermark_column        STRING,
    incremental_filter      STRING,
    active_flag             BOOLEAN
);
```

---

### 7.4 `md_dataset_target`

Stores target contract.

```sql
CREATE TABLE md_dataset_target (
    target_id               STRING,
    dataset_id              STRING,

    target_platform         STRING,
    target_storage_type     STRING,
    target_format           STRING,

    target_connection_name  STRING,
    target_database         STRING,
    target_schema           STRING,
    target_object           STRING,
    target_path             STRING,

    write_mode              STRING,
    write_strategy          STRING,

    partition_columns       STRING,
    primary_key_columns     STRING,
    watermark_column        STRING,

    active_flag             BOOLEAN
);
```

Example values:

| Field | Example |
|---|---|
| target_platform | Databricks |
| target_storage_type | table |
| target_format | delta |
| target_schema | silver |
| target_object | population_by_age |
| write_mode | overwrite |
| write_strategy | full_load |

Other target examples:

| Platform | Storage type | Format | Write strategy |
|---|---|---|---|
| ADLS | file | parquet | incremental |
| OneLake | table | delta | merge |
| Databricks | table | delta | scd2 |
| Snowflake | table | sql_table | merge |
| AzureSQL | table | sql_table | upsert |
| CosmosDB | collection | cosmos_document | upsert |

---

### 7.5 `md_schema_mapping`

Stores source-to-target mapping, aligned to Erwin where possible.

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

---

### 7.6 `md_transformation_rule`

Stores transformation intent.

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

Rule types may include:

- select
- filter
- derive_column
- regex_replace
- cast
- split
- join
- pivot
- aggregate
- deduplicate
- custom_sql
- custom_pyspark
- scd1_merge
- scd2_merge

---

### 7.7 `md_governance_rule`

Stores governance controls.

```sql
CREATE TABLE md_governance_rule (
    governance_rule_id      STRING,
    dataset_id              STRING,
    rule_category           STRING,
    rule_name               STRING,
    rule_expression         STRING,
    severity                STRING,
    enforcement_action      STRING,
    enabled_flag            BOOLEAN
);
```

Governance categories:

- DQ
- PII
- Masking
- Lineage
- Access
- Certification
- Reconciliation
- SchemaDrift
- Retention

Enforcement actions:

- log
- warn
- quarantine
- mask
- fail_pipeline
- require_approval

---

### 7.8 `md_coding_agent_task`

Stores LLM coding agent tasks.

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

Task types:

- generate_transform
- refactor_notebook
- create_tests
- create_docs
- generate_mapping_summary
- suggest_dq_rules
- generate_target_adapter

---

### 7.9 `md_generated_code_asset`

Stores generated code traceability.

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

### 7.10 `md_pipeline_audit_log`

Stores runtime audit history.

```sql
CREATE TABLE md_pipeline_audit_log (
    run_id                  STRING,
    dataset_id              STRING,
    pipeline_name           STRING,
    activity_name           STRING,
    status                  STRING,
    source_record_count     BIGINT,
    target_record_count     BIGINT,
    rejected_record_count   BIGINT,
    warning_count           BIGINT,
    error_message           STRING,
    code_version            STRING,
    metadata_version        STRING,
    started_at              TIMESTAMP,
    completed_at            TIMESTAMP
);
```

---

## 8. Quest Erwin integration

### 8.1 Role of Erwin

Quest Erwin should be the authoritative source for:

- conceptual model
- logical model
- physical model
- entities
- attributes
- data types
- domains
- definitions
- PK/FK relationships
- approved naming standards
- model version
- source-to-target mapping, if maintained in Erwin

### 8.2 Erwin-to-framework flow

```text
Erwin Logical Model
        │
        ▼
Erwin Physical Model
        │
        ▼
Model export
        │
        ▼
Metadata ingestion
        │
        ▼
Framework metadata tables
        │
        ▼
Pipeline validation and code generation
```

### 8.3 Required Erwin exports

At minimum, export:

- entity list
- attribute list
- physical table mappings
- data types
- nullability
- PK/FK relationships
- domain values
- definitions
- data classification
- model version

### 8.4 Erwin mapping to metadata

| Erwin concept | Framework metadata |
|---|---|
| Entity | md_dataset / md_entity |
| Attribute | md_schema_mapping |
| Physical table | md_dataset_target |
| Data type | md_schema_mapping.target_data_type |
| Domain | md_governance_rule / md_reference_domain |
| Relationship | md_relationship / lineage rule |
| Classification | md_governance_rule / sensitivity_class |

---

## 9. LLM coding agent design

### 9.1 Purpose

The LLM coding agent accelerates delivery by generating deterministic engineering artefacts from metadata and transformation contracts.

It can generate:

- PySpark transformation modules
- SQL transformation scripts
- Fabric notebook wrappers
- Databricks notebook wrappers
- target writer adapters
- unit tests
- data reconciliation tests
- documentation
- lineage summaries
- data quality rule suggestions

### 9.2 Agent input contract

The agent should receive a structured contract, not vague instructions.

Example:

```yaml
dataset_id: DS_POP_001
dataset_name: population_by_age

source:
  object: raw_population
  format: csv
  delimiter: tab
  path: /raw/population

lookup:
  object: dim_country
  path: /lookup/dim_country
  join:
    source_key: country_code
    lookup_key: country_code_2_digit

target:
  platform: Databricks
  storage_type: table
  format: delta
  schema: silver
  object: population_by_age
  write_mode: overwrite

transformations:
  - sequence: 10
    type: derive_column
    target_column: age_group
    expression: remove PC_ prefix from first component of source composite column

  - sequence: 20
    type: derive_column
    target_column: country_code
    expression: second component of source composite column split by comma

  - sequence: 30
    type: clean_cast
    source_column: percentage_2019
    target_type: decimal(4,2)

  - sequence: 40
    type: pivot
    group_by: country_code
    pivot_column: age_group
    value_column: percentage_2019

  - sequence: 50
    type: join
    join_type: inner
    lookup: dim_country
```

### 9.3 Agent output contract

The agent should produce:

```text
/transforms/pyspark/population_by_age_transform.py
/tests/unit/test_population_by_age_transform.py
/tests/data/test_population_by_age_reconciliation.py
/notebooks/population_by_age_driver.py
/docs/mappings/population_by_age_mapping.md
```

### 9.4 Agent guardrails

The agent must not:

- deploy directly to production
- access secrets
- approve its own code
- bypass tests
- modify production metadata without approval
- change governance rules without review
- write production data at runtime
- make non-deterministic runtime transformation decisions

---

## 10. Transformation runtime design

### 10.1 Modular transformation pattern

Transformation logic should be implemented as importable modules where possible.

Example:

```python
def transform_population_by_age(df_population, df_country):
    # deterministic transformation logic
    return df_output
```

Notebook wrappers should be thin.

Notebook responsibilities:

- read parameters
- load metadata
- call transformation module
- call governance module
- write target
- log audit outcome

### 10.2 Generic notebook wrapper

```python
dataset_id = get_param("dataset_id")
run_id = get_param("run_id")
environment = get_param("environment")

metadata = load_dataset_metadata(dataset_id)
source = load_source_contract(dataset_id)
target = load_target_contract(dataset_id)
rules = load_transformation_rules(dataset_id)
governance_rules = load_governance_rules(dataset_id)

df_input = read_landed_data(source)
df_output = execute_transform(dataset_id, df_input, rules)
dq_result = run_dq_checks(df_output, governance_rules)

if dq_result.has_critical_failures:
    quarantine_dataset(df_output, dq_result)
    fail_pipeline(dq_result)

write_target(df_output, target)
register_lineage(dataset_id, source, target, rules)
write_audit_log(run_id, dataset_id, "SUCCESS")
```

---

## 11. Target adapter design

### 11.1 Target writer interface

```python
def write_target(df, target_contract):
    platform = target_contract["target_platform"].lower()

    if platform in ["adls", "onelake"]:
        return write_file_target(df, target_contract)

    if platform == "databricks":
        return write_delta_table(df, target_contract)

    if platform == "snowflake":
        return write_snowflake_table(df, target_contract)

    if platform in ["azuresql", "synapsesql"]:
        return write_jdbc_table(df, target_contract)

    if platform == "cosmosdb":
        return write_cosmos_documents(df, target_contract)

    raise ValueError(f"Unsupported target platform: {platform}")
```

### 11.2 Target adapter responsibilities

Each adapter should handle:

- connection retrieval
- write mode
- schema validation
- merge/upsert logic
- partitioning
- error handling
- audit metrics
- target-specific optimisation

### 11.3 Target adapter examples

| Adapter | Target |
|---|---|
| DeltaWriter | ADLS / OneLake / Databricks Delta |
| JdbcWriter | Azure SQL / Synapse SQL |
| SnowflakeWriter | Snowflake |
| CosmosWriter | Cosmos DB |
| FileWriter | CSV / JSON / Parquet |
| ApiWriter | Future API sink |

---

## 12. Governance design

### 12.1 Governance control points

```text
Pre-ingestion
    ├── source registration check
    ├── connection approval check
    └── authorised dataset check

Post-landing
    ├── file arrival check
    ├── row count check
    ├── schema drift check
    └── source reconciliation

Pre-transformation
    ├── mapping completeness check
    ├── mandatory column check
    └── transformation contract validation

Pre-publication
    ├── DQ checks
    ├── PII masking
    ├── duplicate checks
    ├── reference data validation
    └── certification gate

Post-publication
    ├── lineage registration
    ├── audit logging
    ├── release evidence
    └── operational monitoring
```

### 12.2 DQ rule examples

| Rule | Enforcement |
|---|---|
| Primary key must not be null | fail_pipeline |
| Country code must be valid | quarantine |
| Percentage must be numeric | reject record |
| Row count variance within threshold | warn or fail |
| Mandatory target columns mapped | fail_pipeline |

### 12.3 PII control examples

| Classification | Action |
|---|---|
| Email | mask |
| Phone number | mask |
| Tax identifier | tokenize |
| Customer name | role-based masking |
| Free-text sensitive field | quarantine or manual review |

### 12.4 Lineage capture

Lineage should capture:

- source system
- source object
- source column
- target platform
- target object
- target column
- transformation rule
- generated code version
- pipeline run id
- model version
- approval id

---

## 13. CI/CD design with Azure DevOps

### 13.1 Purpose

Azure DevOps should act as the engineering release control plane.

Fabric remains the runtime orchestration layer.

```text
Azure DevOps:
- source control
- pull requests
- CI checks
- approvals
- deployments

Fabric:
- runtime ingestion
- runtime transformation orchestration
- runtime governance activities
```

### 13.2 Azure DevOps flow

```text
LLM coding agent / developer
        │
        ▼
Feature branch
        │
        ▼
Pull request
        │
        ▼
CI pipeline
        │
        ├── metadata validation
        ├── linting
        ├── unit tests
        ├── data tests
        ├── schema compatibility checks
        ├── DQ rule validation
        └── evidence pack generation
        │
        ▼
Approval gate
        │
        ▼
Merge to main
        │
        ▼
CD pipeline
        │
        ├── deploy metadata
        ├── deploy notebooks / packages
        ├── deploy Fabric pipeline artefacts
        ├── deploy Databricks jobs
        ├── deploy SQL objects
        └── run smoke tests
        │
        ▼
Dev → Test → Prod
```

### 13.3 CI checks

| Area | Checks |
|---|---|
| Python | lint, format, unit tests |
| PySpark | local tests where possible, notebook import validation |
| SQL | syntax validation, migration validation |
| Metadata | JSON/YAML schema validation |
| Mapping | source-to-target completeness |
| DQ | required rules present |
| Security | no secrets in code, dependency scan |
| Governance | PII classification, lineage metadata |
| Release | version, changelog, approval owner |

### 13.4 CD deployment targets

| Artefact | Deployment target |
|---|---|
| Fabric pipeline | Fabric workspace |
| Fabric notebook | Fabric workspace |
| Databricks package | Databricks workspace |
| Databricks job | Databricks workflow/job |
| Metadata | metadata database / Delta table |
| SQL objects | Azure SQL / Synapse / Snowflake |
| DQ rules | governance metadata tables |
| Target adapters | Python package / wheel |

---

## 14. Repository scaffold

Recommended starting structure:

```text
fabric-foundry/
│
├── README.md
│
├── docs/
│   ├── architecture.md
│   ├── metadata_model.md
│   ├── operating_model.md
│   ├── onboarding_new_dataset.md
│   ├── governance_design.md
│   └── release_process.md
│
├── fabric/
│   ├── pipelines/
│   │   ├── pl_metadata_driven_ingestion.json
│   │   ├── pl_governance_validation.json
│   │   └── pl_lineage_registration.json
│   │
│   ├── notebooks/
│   │   ├── generic_ingestion_driver.py
│   │   ├── generic_transform_driver.py
│   │   └── generic_governance_driver.py
│   │
│   └── environments/
│       ├── dev.json
│       ├── test.json
│       └── prod.json
│
├── databricks/
│   ├── notebooks/
│   ├── jobs/
│   ├── bundles/
│   └── cluster_policies/
│
├── framework/
│   ├── metadata/
│   │   ├── metadata_reader.py
│   │   ├── metadata_validator.py
│   │   └── contract_loader.py
│   │
│   ├── ingestion/
│   │   ├── source_reader.py
│   │   └── landing_validator.py
│   │
│   ├── transforms/
│   │   ├── rule_engine.py
│   │   ├── transform_registry.py
│   │   └── pyspark_helpers.py
│   │
│   ├── targets/
│   │   ├── target_writer.py
│   │   ├── delta_writer.py
│   │   ├── jdbc_writer.py
│   │   ├── snowflake_writer.py
│   │   ├── cosmos_writer.py
│   │   └── file_writer.py
│   │
│   ├── governance/
│   │   ├── dq_runner.py
│   │   ├── pii_masking.py
│   │   ├── lineage_publisher.py
│   │   └── certification_gate.py
│   │
│   └── audit/
│       ├── audit_logger.py
│       └── evidence_pack.py
│
├── metadata/
│   ├── ddl/
│   │   ├── md_source_system.sql
│   │   ├── md_dataset.sql
│   │   ├── md_dataset_source.sql
│   │   ├── md_dataset_target.sql
│   │   ├── md_schema_mapping.sql
│   │   ├── md_transformation_rule.sql
│   │   ├── md_governance_rule.sql
│   │   ├── md_coding_agent_task.sql
│   │   └── md_pipeline_audit_log.sql
│   │
│   ├── seed/
│   │   ├── population_dataset.yaml
│   │   ├── population_mapping.yaml
│   │   └── population_governance_rules.yaml
│   │
│   └── contracts/
│       └── population_by_age_contract.yaml
│
├── erwin/
│   ├── exports/
│   ├── model_ingestion/
│   └── mapping_templates/
│
├── agent/
│   ├── prompts/
│   │   ├── generate_transform.md
│   │   ├── generate_tests.md
│   │   └── review_code.md
│   │
│   ├── contracts/
│   └── generated_assets/
│
├── transforms/
│   └── pyspark/
│       └── population_by_age_transform.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── data_quality/
│   ├── reconciliation/
│   └── contract/
│
├── infra/
│   ├── bicep/
│   ├── terraform/
│   └── arm/
│
└── azure-pipelines/
    ├── ci.yml
    ├── cd-dev.yml
    ├── cd-test.yml
    └── cd-prod.yml
```

---

## 15. Example population dataset scaffold

### 15.1 Dataset contract

```yaml
dataset_id: DS_POP_001
dataset_name: population_by_age
business_domain: reference_data
load_type: full
frequency: on_demand

source:
  source_system: ADLS_RAW
  source_type: file
  format: csv
  delimiter: tab
  path: /raw/population

lookup:
  name: dim_country
  format: csv
  delimiter: comma
  path: /lookup/dim_country

target:
  platform: Databricks
  storage_type: table
  format: delta
  schema: silver
  object: population_by_age
  write_mode: overwrite
  write_strategy: full_load

governance:
  dq_required: true
  pii_classification_required: false
  lineage_required: true
  certification_required: true
```

### 15.2 Transformation rule summary

```yaml
rules:
  - sequence: 10
    name: extract_age_group
    type: derive_column
    target_column: age_group

  - sequence: 20
    name: extract_country_code
    type: derive_column
    target_column: country_code

  - sequence: 30
    name: clean_percentage
    type: regex_clean_cast
    target_column: percentage_2019

  - sequence: 40
    name: pivot_age_group
    type: pivot

  - sequence: 50
    name: join_country_lookup
    type: join
```

---

## 16. Delivery phases

The delivery phases are intentionally staged so the MVP can prove the reusable ingestion and transformation pattern first, while still leaving room for stronger model governance, platform metadata acquisition and source-to-target reconciliation later.

## Phase 0 — Foundation and design baseline

### Objective

Establish the architecture baseline, repository scaffold and delivery standards.

### Scope

- Confirm target architecture
- Define MVP boundaries
- Create Git repository
- Create folder scaffold
- Define naming standards
- Define environment naming
- Define metadata standards
- Define coding standards
- Define review and approval model

### Deliverables

- Architecture design document
- Repository scaffold
- Metadata model draft
- Dataset onboarding template
- Transformation contract template
- Governance control point design
- Delivery roadmap

### Exit criteria

- Architecture approved
- Repo created
- Initial scaffold committed
- MVP dataset selected
- Design principles agreed

---

## Phase 1 — Metadata-driven ingestion MVP

### Objective

Build the first reusable ingestion pipeline driven by metadata.

### Scope

- Create core metadata tables:
  - md_source_system
  - md_dataset
  - md_dataset_source
  - md_dataset_target
  - md_pipeline_audit_log
- Create generic Fabric pipeline:
  - metadata lookup
  - ForEach dataset
  - Copy Activity
  - landing validation
  - audit logging
- Onboard first sample dataset
- Land raw data to ADLS / OneLake / Lakehouse

### Deliverables

- Generic ingestion pipeline
- Metadata DDL
- Dataset seed metadata
- Audit logging
- Landing validation
- Sample run evidence

### Exit criteria

- One dataset can be ingested without hardcoded pipeline logic
- Run audit is captured
- Failures are logged
- Dataset metadata can be changed without editing the pipeline

---

## Phase 1A — Erwin metadata ingestion and platform metadata acquisition

### Objective

Introduce a formal metadata acquisition layer so the framework can source dataset design metadata from Quest Erwin and actual physical metadata from source and target platforms.

This phase creates the foundation for model-driven pipeline generation, even if full source-to-target reconciliation is deferred to a later QA phase.

### Scope

#### Erwin metadata ingestion

- Define standard Erwin export/report formats
- Land Erwin model metadata into a controlled metadata landing zone
- Capture Erwin model version
- Load Erwin exports into staging tables
- Standardise Erwin entity, table, attribute and column names
- Capture physical model metadata
- Capture source-to-target mapping metadata where available
- Capture business definitions, domains and classifications where available
- Map Erwin metadata into framework metadata tables

#### Source and target metadata acquisition by platform

Capture actual platform metadata from:

- Azure Synapse
- Azure SQL Database
- ADLS Gen2
- OneLake / Fabric Lakehouse
- Databricks / Unity Catalog
- Snowflake
- Cosmos DB
- Other future registered platforms

The purpose is to build a physical metadata inventory, not yet to enforce full reconciliation.

### Metadata acquisition patterns

```text
Quest Erwin
    ↓
Erwin export / report / repository extract
    ↓
stg_erwin_* tables
    ↓
framework metadata tables

Source / target platforms
    ↓
platform discovery queries / profiling jobs
    ↓
disc_platform_* tables
    ↓
metadata inventory
```

### Key metadata captured from Erwin

- model name
- model version
- subject area
- entity name
- attribute name
- physical table name
- physical column name
- data type
- nullability
- primary key / foreign key indicators
- business definition
- domain
- data classification
- source object
- target object
- source-to-target mapping
- transformation description

### Key metadata captured from platforms

| Platform | Metadata acquisition method |
|---|---|
| Azure SQL / Synapse SQL | `INFORMATION_SCHEMA`, system catalog views |
| Snowflake | `INFORMATION_SCHEMA`, account usage views |
| Databricks / Unity Catalog | catalog/schema/table metadata, `DESCRIBE TABLE`, information schema |
| ADLS / OneLake | file profiling, inferred schema, file format, path, partition pattern |
| Cosmos DB | database/container metadata, partition key, indexing policy, sampled document profile |
| Fabric Lakehouse | workspace/lakehouse/table metadata, Delta schema, file/table inventory |

### New staging tables

```sql
CREATE TABLE stg_erwin_model (
    model_version_id        STRING,
    model_name              STRING,
    erwin_model_version     STRING,
    export_timestamp        TIMESTAMP,
    import_status           STRING
);
```

```sql
CREATE TABLE stg_erwin_object (
    model_version_id        STRING,
    subject_area            STRING,
    logical_entity_name     STRING,
    physical_object_name    STRING,
    object_type             STRING,
    platform_hint           STRING
);
```

```sql
CREATE TABLE stg_erwin_column (
    model_version_id        STRING,
    physical_object_name    STRING,
    physical_column_name    STRING,
    logical_attribute_name  STRING,
    data_type               STRING,
    nullable_flag           BOOLEAN,
    primary_key_flag        BOOLEAN,
    business_definition     STRING,
    domain_name             STRING,
    classification          STRING
);
```

```sql
CREATE TABLE stg_erwin_mapping (
    model_version_id        STRING,
    source_system_name      STRING,
    source_object_name      STRING,
    source_column_name      STRING,
    target_system_name      STRING,
    target_object_name      STRING,
    target_column_name      STRING,
    transformation_text     STRING,
    business_definition     STRING,
    classification          STRING
);
```

```sql
CREATE TABLE disc_platform_object (
    discovery_run_id        STRING,
    platform_name           STRING,
    database_name           STRING,
    schema_name             STRING,
    object_name             STRING,
    object_type             STRING,
    discovered_at           TIMESTAMP
);
```

```sql
CREATE TABLE disc_platform_column (
    discovery_run_id        STRING,
    platform_name           STRING,
    database_name           STRING,
    schema_name             STRING,
    object_name             STRING,
    column_name             STRING,
    data_type               STRING,
    nullable_flag           BOOLEAN,
    ordinal_position        INT,
    discovered_at           TIMESTAMP
);
```

### Deliverables

- `pl_ingest_erwin_metadata`
- Erwin export/report specification
- Erwin metadata landing folder
- Erwin staging tables
- platform discovery scripts/notebooks
- platform discovery staging tables
- initial Erwin-to-framework metadata mapping
- metadata acquisition audit log
- metadata inventory report

### Exit criteria

- Erwin export can be loaded into staging tables
- model version is captured
- source and target dataset metadata can be created from Erwin metadata
- at least one platform discovery process can capture actual table/file metadata
- metadata acquisition output is available for later reconciliation

---

## Phase 2 — Transformation framework MVP

### Objective

Introduce reusable transformation execution using notebooks and transformation contracts.

### Scope

- Create transformation contract format
- Create generic transformation notebook wrapper
- Create transformation module pattern
- Refactor sample transformation into reusable module
- Introduce target writer interface
- Support first target:
  - Delta table or ADLS/OneLake parquet/delta
- Add schema mapping metadata

### Deliverables

- md_schema_mapping
- md_transformation_rule
- generic transform driver notebook
- rule engine v0.1
- target writer v0.1
- sample population transformation module
- unit tests for transformation logic

### Exit criteria

- Sample dataset can be transformed using framework structure
- Transformation logic is outside hardcoded pipeline activities
- Target write is controlled through target contract
- Output matches expected sample results

---

## Phase 3 — Multi-target adapter support

### Objective

Extend the framework to support different target platforms.

### Scope

Implement target adapters for:

- Delta / Lakehouse
- ADLS / OneLake file target
- Azure SQL / Synapse SQL through JDBC
- Snowflake
- Cosmos DB

### Deliverables

- target_writer.py interface
- delta_writer.py
- jdbc_writer.py
- snowflake_writer.py
- cosmos_writer.py
- file_writer.py
- target contract validation
- write strategy metadata

### Exit criteria

- Same transformation output can be routed to different target platforms through metadata
- Target-specific write logic is isolated
- Unsupported platforms fail gracefully
- Audit captures target write metrics

---

## Phase 4 — LLM coding agent integration

### Objective

Introduce an LLM coding agent to generate transformation assets from metadata contracts.

### Scope

- Define agent prompts
- Define agent input contract
- Define agent output contract
- Generate transformation code from sample contract
- Generate unit tests
- Generate mapping documentation
- Register generated code assets in metadata
- Require pull request review

### Deliverables

- agent prompt templates
- md_coding_agent_task
- md_generated_code_asset
- generated sample transformation module
- generated unit tests
- generated documentation
- PR review checklist

### Exit criteria

- Agent can generate a transformation module from a contract
- Agent output is committed to Git
- Tests are generated and runnable
- Generated code is not deployed without approval
- Agent activity is traceable

---

## Phase 5 — Governance control gates

### Objective

Add executable governance controls into the framework.

### Scope

- Add DQ rule metadata
- Add DQ runner
- Add schema drift detection
- Add PII classification support
- Add masking rule support
- Add lineage registration pattern
- Add certification gate
- Add quarantine handling

### Deliverables

- md_governance_rule
- dq_runner.py
- pii_masking.py
- lineage_publisher.py
- certification_gate.py
- quarantine path/table
- governance audit log
- evidence pack

### Exit criteria

- Critical DQ failures can stop a pipeline
- Warning rules can log without stopping
- PII rules can mask or quarantine data
- Lineage is captured at source/target/rule level
- Certified output is explicitly marked

---

## Phase 6 — Azure DevOps CI/CD integration

### Objective

Move from manual deployment to controlled CI/CD.

### Scope

- Create Azure DevOps pipeline templates
- Add PR validation
- Add metadata validation
- Add code linting
- Add unit tests
- Add data contract tests
- Add deployment stages
- Add approval gates
- Deploy to dev/test/prod

### Deliverables

- ci.yml
- cd-dev.yml
- cd-test.yml
- cd-prod.yml
- PR policy
- environment variable structure
- service connection design
- release evidence report

### Exit criteria

- Pull request triggers CI
- Main branch merge triggers CD to dev
- Test/prod require approval
- Artefacts are versioned
- Deployment is repeatable
- Rollback approach is documented

---

## Phase 6A — Source-to-target reconciliation QA

### Objective

Introduce a formal QA phase that reconciles approved Erwin metadata, framework execution metadata and actual platform metadata before large-scale production adoption.

This is intentionally a later phase because it requires stable Erwin ingestion, stable platform discovery, mature metadata ownership and reliable CI/CD evidence.

### Scope

- Compare Erwin intended design against actual deployed source and target platforms
- Compare Erwin source-to-target mappings against framework transformation contracts
- Compare target schemas against generated transformation outputs
- Detect schema drift between model, metadata and platform
- Detect missing source-to-target mappings
- Detect unmapped mandatory target columns
- Detect data type, nullability and precision/scale mismatches
- Detect missing governance classification
- Detect missing DQ rules for critical fields
- Detect missing lineage for certified outputs
- Produce reconciliation QA evidence pack
- Raise defects or approval tasks for unresolved gaps

### Reconciliation model

```text
Erwin metadata
    = intended model and approved mapping

Framework metadata
    = executable contract used by the pipeline

Platform discovery metadata
    = actual deployed state

Reconciliation QA
    = evidence that all three are aligned
```

### Reconciliation checks

| Check type | Example |
|---|---|
| Object existence | Erwin defines `DIM_CUSTOMER`, but Snowflake table is missing |
| Extra object | Platform has a table that is not registered in Erwin/framework metadata |
| Column existence | Target column exists in model but not in platform |
| Extra column | Platform has a column not defined in Erwin |
| Data type mismatch | Erwin says `DECIMAL(18,2)`, target is `FLOAT` |
| Nullability mismatch | Erwin says `NOT NULL`, target allows null |
| Primary key mismatch | Erwin PK does not match target metadata |
| Mapping gap | Target column has no approved source mapping |
| Transformation gap | Mapping exists but no transformation rule or code asset exists |
| Governance gap | PII column has no masking or access rule |
| DQ gap | Critical field has no DQ validation rule |
| Lineage gap | Certified output has incomplete source-to-target lineage |

### Reconciliation severity

| Severity | Meaning | Action |
|---|---|---|
| Critical | Could produce incorrect or non-compliant production data | block release |
| High | Material design or implementation gap | require approval or remediation |
| Medium | Non-blocking but should be fixed | log defect |
| Low | Documentation or naming inconsistency | log issue |

### New QA metadata tables

```sql
CREATE TABLE md_reconciliation_run (
    reconciliation_run_id   STRING,
    model_version_id        STRING,
    discovery_run_id        STRING,
    environment             STRING,
    reconciliation_scope    STRING,
    started_at              TIMESTAMP,
    completed_at            TIMESTAMP,
    status                  STRING
);
```

```sql
CREATE TABLE md_reconciliation_result (
    reconciliation_run_id   STRING,
    dataset_id              STRING,
    check_type              STRING,
    object_name             STRING,
    column_name             STRING,
    erwin_value             STRING,
    framework_value         STRING,
    discovered_value        STRING,
    severity                STRING,
    result_status           STRING,
    recommendation          STRING,
    created_at              TIMESTAMP
);
```

### Deliverables

- source-to-target reconciliation QA process
- reconciliation rules library
- reconciliation metadata tables
- reconciliation evidence pack
- schema drift report
- mapping gap report
- governance gap report
- QA sign-off workflow
- release blocking criteria

### Exit criteria

- Reconciliation can compare Erwin, framework metadata and platform discovery metadata
- Critical reconciliation failures can block production release
- Reconciliation results are auditable
- QA evidence can be attached to release approval
- Data owner / modeller / engineer remediation workflow is defined

---

## Phase 7 — Operational monitoring and support model

### Objective

Operationalise the framework for production support.

### Scope

- Add monitoring dashboard
- Add pipeline SLA tracking
- Add failed run alerting
- Add data freshness tracking
- Add reconciliation reporting
- Add support runbook
- Add onboarding guide
- Add data product certification dashboard

### Deliverables

- Operational dashboard
- SLA metrics
- Failure alert design
- Runbook
- Onboarding guide
- Support model
- Ownership matrix

### Exit criteria

- Support team can diagnose failures
- Business users can see data freshness and certification state
- Data owners can see DQ exceptions
- Engineering can trace runs to code and metadata versions

---

## Phase 8 — Enterprise scale hardening

### Objective

Harden the framework for multiple domains and enterprise adoption.

### Scope

- Multi-domain onboarding
- Multi-workspace deployment
- Secrets and managed identity hardening
- Performance tuning
- Cost monitoring
- Parallel execution controls
- Reusable templates
- Platform governance integration
- Enterprise metadata catalogue integration

### Deliverables

- Multi-domain configuration
- Performance tuning guide
- Cost optimisation guide
- Security hardening guide
- Enterprise onboarding playbook
- Framework maturity assessment

### Exit criteria

- Multiple datasets and domains onboarded
- Platform can scale without duplicating pipelines
- Governance controls are reusable
- CI/CD and release controls are stable
- Framework is ready as reusable enterprise accelerator

---

## 17. MVP recommendation

The recommended MVP should include only enough to prove the pattern.

### MVP scope

```text
Phase 0: Foundation
Phase 1: Metadata-driven ingestion
Phase 1A: Lightweight Erwin export ingestion / platform metadata acquisition for one sample dataset
Phase 2: Transformation framework MVP
Partial Phase 4: LLM-generated transformation code for one dataset
```

Phase 6A source-to-target reconciliation QA should remain out of MVP scope. It should be introduced later when metadata acquisition, CI/CD, model ownership and governance processes are mature enough to support formal release blocking.

### MVP target outcome

By the end of MVP, demonstrate:

```text
One dataset onboarded through metadata
        ↓
Raw data landed through generic ingestion
        ↓
Transformation generated/refactored from contract
        ↓
Transformation executed through notebook wrapper
        ↓
Output written to Delta or ADLS/OneLake
        ↓
Audit record captured
        ↓
Code version and metadata version traceable
```

### MVP success statement

> A new dataset can be onboarded by creating metadata and transformation contracts, not by building a bespoke pipeline from scratch.

---

## 18. Key risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Too much logic in Fabric pipeline | Framework becomes hard to reuse | Keep business logic in metadata and code modules |
| LLM-generated code bypasses review | Production data risk | Require PR, tests and approval |
| Metadata becomes too complex too early | MVP slows down | Start with minimum viable metadata |
| Target platforms handled inconsistently | Duplicated logic | Use target adapter interface |
| Governance added too late | Rework and compliance gaps | Add governance hooks from Phase 1 |
| Erwin export is inconsistent | Mapping errors | Validate model export before ingestion |
| CI/CD delayed too long | Manual deployment risk | Version files from day one |
| Secrets in notebooks | Security risk | Use managed identity / service connections / Key Vault |
| DQ rules are not owned | Governance ambiguity | Assign data owner and steward |
| Runtime LLM usage creates non-determinism | Audit and repeatability risk | Keep LLM at build-time only |

---

## 19. Recommended immediate next steps

1. Create the repository scaffold.
2. Create metadata DDL files.
3. Define the Erwin export/report structure for the first sample dataset.
4. Add lightweight Erwin metadata ingestion into staging tables.
5. Add lightweight platform metadata acquisition for the first source and target platform.
6. Convert the existing population transformation into a contract.
7. Refactor the current transformation notebook into:
   - transformation module
   - thin notebook driver
   - unit test
   - target writer
8. Build the first Fabric pipeline:
   - lookup metadata
   - copy activity
   - notebook activity
   - audit activity
9. Add a basic coding agent prompt:
   - generate PySpark transform from contract
   - generate unit tests
   - generate mapping documentation
10. Add a manual review gate before production use.
11. Defer formal source-to-target reconciliation QA until the later QA phase.

---

## 20. Architecture one-liner

> This framework uses Fabric pipelines as the orchestration layer, metadata as the execution contract, Quest Erwin as the modelling authority, an LLM coding agent as the build-time engineering accelerator, and Azure DevOps as the future release control plane, with governance controls embedded as reusable gates across ingestion, transformation and publication.
