# SPEC.md — Phase 1: Metadata-Driven Ingestion

## 1. Phase objective

Build the first reusable ingestion capability where source-to-raw or source-to-bronze data movement is driven by metadata rather than hardcoded one-off pipelines.

The goal is to prove that a new dataset can be onboarded by registering metadata and using the same generic ingestion pipeline.

---

## 2. Phase scope

### In scope

- Implement minimum viable metadata tables for ingestion
- Create source system metadata
- Create dataset metadata
- Create source contract metadata
- Create target contract metadata
- Create pipeline audit logging
- Create generic Fabric ingestion pipeline
- Create landing validation step
- Onboard one sample dataset
- Land data into raw/bronze zone
- Log run result

### Out of scope

- Full transformation framework
- LLM code generation
- Full DQ engine
- PII masking
- Source-to-target reconciliation QA
- Full CI/CD
- Production-grade monitoring
- Multi-target adapters beyond raw landing requirement

---

## 3. Functional requirements

### FR-001 — Register source systems

The framework must allow source systems to be registered in metadata.

Required attributes:

- source system id
- source system name
- source type
- connection name
- authentication method
- owner
- active flag

Supported MVP source types:

- ADLS
- Synapse SQL
- Azure SQL
- file-based source

---

### FR-002 — Register datasets

The framework must allow datasets to be registered independently from physical source and target details.

Required attributes:

- dataset id
- dataset name
- business domain
- source system id
- data owner
- data steward
- load type
- frequency
- active flag

---

### FR-003 — Register dataset source contract

The framework must capture where and how to read a dataset.

Required attributes:

- dataset id
- source object type
- source database
- source schema
- source object
- source path
- source format
- delimiter
- watermark column
- incremental filter

---

### FR-004 — Register dataset target contract

The framework must capture where and how to land the data.

Required attributes:

- dataset id
- target platform
- target storage type
- target format
- target database
- target schema
- target object
- target path
- write mode
- write strategy

---

### FR-005 — Generic ingestion pipeline

The framework must provide a generic Fabric pipeline that:

```text
1. creates run id
2. loads active dataset metadata
3. iterates over selected datasets
4. reads source contract
5. reads target contract
6. executes Copy Activity or equivalent ingestion activity
7. validates landing result
8. writes audit log
```

---

### FR-006 — Parameterised execution

The pipeline must support parameters:

| Parameter | Purpose |
|---|---|
| environment | dev/test/prod |
| dataset_id | run a single dataset |
| dataset_group | run a group of datasets |
| run_mode | manual/scheduled/retry |
| batch_date | logical batch date |
| full_refresh_flag | override incremental behaviour |

---

### FR-007 — Landing validation

After ingestion, the framework must validate:

- target path exists
- file/table created
- row count captured where possible
- source count captured where possible
- target count captured where possible
- zero-row handling is logged
- failure is captured in audit log

---

### FR-008 — Audit logging

Each pipeline run must create audit records.

Minimum fields:

- run id
- dataset id
- pipeline name
- activity name
- status
- source record count
- target record count
- rejected record count
- warning count
- error message
- started timestamp
- completed timestamp

---

## 4. Non-functional requirements

### NFR-001 — Reusability

The pipeline must not be specific to the sample dataset.

### NFR-002 — Configurability

Environment-specific values must be externalised.

### NFR-003 — Observability

Each run must have an auditable status.

### NFR-004 — Failure handling

Pipeline failure must be logged with meaningful error details.

### NFR-005 — Security

No secrets may be stored in notebooks, pipeline definitions or metadata seed files.

### NFR-006 — Extensibility

The ingestion pattern must allow future support for additional platforms.

---

## 5. Metadata DDL

### 5.1 `md_source_system`

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

### 5.2 `md_dataset`

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

### 5.3 `md_dataset_source`

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

### 5.4 `md_dataset_target`

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

### 5.5 `md_pipeline_audit_log`

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

## 6. Sample dataset metadata

### 6.1 Source system

```yaml
source_system_id: SRC_ADLS_REF_001
source_system_name: ADLS Reference Data
source_type: ADLS
connection_name: conn_adls_reference
auth_method: managed_identity
owner: data_platform
active_flag: true
```

### 6.2 Dataset

```yaml
dataset_id: DS_REF_POPULATION_001
dataset_name: population_by_age
business_domain: reference_data
source_system_id: SRC_ADLS_REF_001
data_owner: reference_data_owner
data_steward: reference_data_steward
sensitivity_class: public
load_frequency: on_demand
load_type: full
active_flag: true
```

### 6.3 Dataset source

```yaml
dataset_source_id: DSS_REF_POPULATION_001
dataset_id: DS_REF_POPULATION_001
source_object_type: file
source_path: /raw/population
source_format: csv
source_delimiter: tab
active_flag: true
```

### 6.4 Dataset target

```yaml
target_id: TGT_RAW_POPULATION_001
dataset_id: DS_REF_POPULATION_001
target_platform: ADLS
target_storage_type: file
target_format: csv
target_path: /landing/reference/population_by_age/
write_mode: overwrite
write_strategy: full_load
active_flag: true
```

---

## 7. Pipeline design

### 7.1 Pipeline name

```text
pl_metadata_driven_ingestion
```

### 7.2 Pipeline activities

```text
Start
 │
 ▼
Initialise run
 │
 ▼
Lookup active datasets
 │
 ▼
ForEach dataset
 │
 ├── Load source metadata
 ├── Load target metadata
 ├── Validate metadata completeness
 ├── Copy source to landing target
 ├── Capture source count
 ├── Capture target count
 ├── Validate landing
 └── Write audit log
 │
 ▼
Finalise run
```

### 7.3 Activity details

| Activity | Type | Purpose |
|---|---|---|
| InitialiseRun | Set variable / notebook / script | Generate run id |
| LookupDatasets | Lookup | Read active datasets |
| ForEachDataset | ForEach | Iterate datasets |
| LookupSource | Lookup | Read source metadata |
| LookupTarget | Lookup | Read target metadata |
| ValidateMetadata | Notebook / script | Ensure required fields exist |
| CopyData | Copy Activity | Move source data to target |
| LandingValidation | Notebook / script | Validate output exists |
| WriteAudit | Notebook / SQL | Insert audit record |

---

## 8. Landing validation design

### 8.1 Validation rules

| Rule | Severity | Action |
|---|---|---|
| Target path exists | critical | fail |
| Target row count available | warning | log |
| Target row count = 0 | warning or critical | configurable |
| Source row count != target row count | warning | log |
| Copy activity failed | critical | fail |
| Metadata missing | critical | fail |

### 8.2 Validation output

```json
{
  "run_id": "RUN_20260519_001",
  "dataset_id": "DS_REF_POPULATION_001",
  "validation_status": "PASSED",
  "source_record_count": 100,
  "target_record_count": 100,
  "warnings": []
}
```

---

## 9. Error handling

### 9.1 Error categories

| Category | Example | Action |
|---|---|---|
| MetadataError | missing source path | fail dataset |
| ConnectionError | connection failed | fail dataset |
| CopyError | copy activity failed | fail dataset |
| ValidationError | target path missing | fail dataset |
| CountMismatch | source/target mismatch | warn or fail based on config |

### 9.2 Retry behaviour

For MVP:

- retry transient copy failures
- do not retry metadata errors
- log all retries
- do not auto-retry if target validation fails due to schema/path issue

---

## 10. Security design

### 10.1 Secrets

Secrets must be stored in:

- Azure Key Vault
- Fabric connection
- Managed identity
- Databricks secret scope, if Databricks is used later

### 10.2 Prohibited

Do not store secrets in:

- notebook source
- metadata YAML
- pipeline JSON
- Git repo
- comments
- generated code

---

## 11. Deliverables

Phase 1 must produce:

- metadata DDL for ingestion
- sample dataset metadata seed
- generic ingestion pipeline design
- generic ingestion pipeline implementation
- landing validation notebook/script
- audit logger
- successful sample ingestion run
- run evidence file

---

## 12. Acceptance criteria

Phase 1 is complete when:

- one sample dataset is ingested using metadata
- no dataset-specific copy logic is hardcoded in the pipeline
- run audit is captured
- landing validation is performed
- failures are logged
- source and target metadata can be changed without editing pipeline logic
- pipeline can be re-run for the sample dataset

---

## 13. Test scenarios

| Scenario | Expected result |
|---|---|
| Valid metadata and valid source file | ingestion succeeds |
| Missing source path | pipeline fails with metadata error |
| Invalid target path | pipeline fails with validation error |
| Empty source file | warning or failure based on config |
| Copy failure | audit record captures failure |
| Re-run full load | target overwritten successfully |

---

## 14. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Copy Activity cannot support all future targets | Introduce adapter pattern later |
| Metadata gaps cause runtime failure | Add metadata validation before copy |
| Hardcoded sample logic creeps into pipeline | Review pipeline JSON and notebook code |
| Counts unavailable for some sources | Make count capture best-effort and configurable |
