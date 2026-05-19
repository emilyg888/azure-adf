# SPEC.md — Phase 1A: Lightweight Erwin Export Ingestion and Platform Metadata Acquisition

## 1. Phase objective

Create a lightweight metadata acquisition capability that can ingest one Quest Erwin export and profile one source/target platform for the MVP sample dataset.

This phase establishes the model-driven foundation for the framework without implementing full enterprise-scale reconciliation.

The guiding principle:

> Erwin provides the intended model.  
> Platform discovery captures the actual physical state.  
> Full reconciliation is deferred to a later QA phase.

---

## 2. Phase scope

### In scope

- Define Erwin export/report format for one sample dataset
- Create Erwin metadata landing path
- Create Erwin staging tables
- Load Erwin export into staging tables
- Capture Erwin model version
- Map Erwin metadata into framework metadata
- Create lightweight platform discovery process
- Capture physical metadata for one source or target platform
- Store platform metadata in discovery tables
- Produce metadata acquisition report

### Out of scope

- Full automated Erwin Mart integration
- Full enterprise model ingestion
- Full source-to-target reconciliation QA
- Release blocking based on reconciliation
- Complete lineage graph
- Catalogue integration
- Purview integration
- Metadata stewardship workflow

---

## 3. Architecture context

```text
Quest Erwin
    │
    │ export/report
    ▼
Erwin metadata landing
    │
    ▼
stg_erwin_* tables
    │
    ▼
framework metadata tables
    │
    ▼
dataset contracts and transformation contracts


Source / target platform
    │
    │ discovery query / profiling script
    ▼
disc_platform_* tables
    │
    ▼
metadata inventory
```

---

## 4. Erwin metadata ingestion design

### 4.1 Erwin export location

Land Erwin exports under:

```text
erwin/exports/<model_name>/<model_version>/
```

Example:

```text
erwin/exports/reference_data_model/v0_1/
    erwin_model.csv
    erwin_objects.csv
    erwin_columns.csv
    erwin_mappings.csv
```

### 4.2 Required Erwin export files for MVP

| File | Purpose |
|---|---|
| erwin_model.csv | model name, model version, export timestamp |
| erwin_objects.csv | logical and physical object metadata |
| erwin_columns.csv | logical and physical column metadata |
| erwin_mappings.csv | source-to-target mappings, if available |

### 4.3 Optional Erwin export files

| File | Purpose |
|---|---|
| erwin_domains.csv | valid values or domain metadata |
| erwin_relationships.csv | PK/FK and entity relationships |
| erwin_classifications.csv | PII or sensitivity classification |
| erwin_definitions.csv | business definitions |

---

## 5. Erwin export file specifications

### 5.1 `erwin_model.csv`

Columns:

```text
model_name
model_version
subject_area
export_timestamp
exported_by
```

### 5.2 `erwin_objects.csv`

Columns:

```text
model_name
model_version
subject_area
logical_entity_name
physical_object_name
object_type
platform_hint
description
```

### 5.3 `erwin_columns.csv`

Columns:

```text
model_name
model_version
physical_object_name
logical_attribute_name
physical_column_name
data_type
length
precision
scale
nullable_flag
primary_key_flag
business_definition
domain_name
classification
```

### 5.4 `erwin_mappings.csv`

Columns:

```text
model_name
model_version
source_system_name
source_object_name
source_column_name
target_system_name
target_object_name
target_column_name
transformation_text
business_definition
classification
```

---

## 6. Erwin staging tables

### 6.1 `stg_erwin_model`

```sql
CREATE TABLE stg_erwin_model (
    model_version_id        STRING,
    model_name              STRING,
    erwin_model_version     STRING,
    subject_area            STRING,
    export_timestamp        TIMESTAMP,
    exported_by             STRING,
    import_status           STRING,
    imported_at             TIMESTAMP
);
```

### 6.2 `stg_erwin_object`

```sql
CREATE TABLE stg_erwin_object (
    model_version_id        STRING,
    model_name              STRING,
    erwin_model_version     STRING,
    subject_area            STRING,
    logical_entity_name     STRING,
    physical_object_name    STRING,
    object_type             STRING,
    platform_hint           STRING,
    description             STRING
);
```

### 6.3 `stg_erwin_column`

```sql
CREATE TABLE stg_erwin_column (
    model_version_id        STRING,
    model_name              STRING,
    erwin_model_version     STRING,
    physical_object_name    STRING,
    logical_attribute_name  STRING,
    physical_column_name    STRING,
    data_type               STRING,
    length                  INT,
    precision_value         INT,
    scale_value             INT,
    nullable_flag           BOOLEAN,
    primary_key_flag        BOOLEAN,
    business_definition     STRING,
    domain_name             STRING,
    classification          STRING
);
```

### 6.4 `stg_erwin_mapping`

```sql
CREATE TABLE stg_erwin_mapping (
    model_version_id        STRING,
    model_name              STRING,
    erwin_model_version     STRING,
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

---

## 7. Framework mapping from Erwin

### 7.1 Mapping logic

| Erwin staging | Framework metadata |
|---|---|
| stg_erwin_model | md_model_version |
| stg_erwin_object | md_dataset / md_dataset_target |
| stg_erwin_column | md_schema_mapping |
| stg_erwin_mapping | md_schema_mapping / md_transformation_rule |
| classification | md_dataset.sensitivity_class / md_governance_rule later |
| business_definition | md_schema_mapping.business_definition |

### 7.2 `md_model_version`

```sql
CREATE TABLE md_model_version (
    model_version_id        STRING,
    model_name              STRING,
    erwin_model_version     STRING,
    export_timestamp        TIMESTAMP,
    export_source           STRING,
    imported_by             STRING,
    import_status           STRING,
    active_flag             BOOLEAN
);
```

---

## 8. Platform metadata acquisition design

### 8.1 Purpose

Platform discovery captures the actual physical metadata from source and target systems.

This is not full reconciliation yet. It creates the inventory needed for later QA.

### 8.2 Supported MVP platform discovery

Pick one or two from:

- ADLS file profile for the source dataset
- Delta / Databricks table profile for the target
- Fabric Lakehouse table profile
- Azure SQL information schema
- Snowflake information schema

For the population MVP, a practical starting point is:

```text
ADLS raw file profiling
Delta or Lakehouse target table schema discovery
```

---

## 9. Discovery staging tables

### 9.1 `disc_platform_object`

```sql
CREATE TABLE disc_platform_object (
    discovery_run_id        STRING,
    platform_name           STRING,
    database_name           STRING,
    schema_name             STRING,
    object_name             STRING,
    object_type             STRING,
    object_path             STRING,
    file_format             STRING,
    discovered_at           TIMESTAMP
);
```

### 9.2 `disc_platform_column`

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
    sample_value            STRING,
    discovered_at           TIMESTAMP
);
```

### 9.3 `disc_file_profile`

```sql
CREATE TABLE disc_file_profile (
    discovery_run_id        STRING,
    dataset_id              STRING,
    path                    STRING,
    file_format             STRING,
    delimiter               STRING,
    header_flag             BOOLEAN,
    file_count              BIGINT,
    total_size_bytes        BIGINT,
    inferred_column_count   INT,
    sample_row_count        BIGINT,
    latest_modified_at      TIMESTAMP,
    discovered_at           TIMESTAMP
);
```

---

## 10. Platform discovery implementation patterns

### 10.1 SQL platform discovery

For Azure SQL / Synapse / Snowflake-like platforms:

```sql
SELECT
    TABLE_CATALOG,
    TABLE_SCHEMA,
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    ORDINAL_POSITION
FROM INFORMATION_SCHEMA.COLUMNS;
```

### 10.2 Databricks / Delta discovery

Use:

```sql
SHOW CATALOGS;
SHOW SCHEMAS IN <catalog>;
SHOW TABLES IN <catalog>.<schema>;
DESCRIBE TABLE EXTENDED <catalog>.<schema>.<table>;
```

### 10.3 ADLS / OneLake file discovery

Use PySpark or Fabric notebook to capture:

- path exists
- file count
- file size
- file format
- inferred schema
- header
- delimiter
- sample values
- modified timestamp

### 10.4 Cosmos DB discovery

For Cosmos DB, capture:

- database
- container
- partition key
- indexing policy
- sample document fields
- inferred field types
- nested field paths

---

## 11. Phase 1A pipeline design

### 11.1 Pipeline names

```text
pl_ingest_erwin_metadata
pl_platform_metadata_discovery
```

### 11.2 `pl_ingest_erwin_metadata`

```text
Start
 │
 ▼
Read Erwin export path
 │
 ▼
Load erwin_model.csv
 │
 ▼
Load erwin_objects.csv
 │
 ▼
Load erwin_columns.csv
 │
 ▼
Load erwin_mappings.csv
 │
 ▼
Validate required columns
 │
 ▼
Create model_version_id
 │
 ▼
Write staging tables
 │
 ▼
Map to framework metadata
 │
 ▼
Write metadata acquisition audit
```

### 11.3 `pl_platform_metadata_discovery`

```text
Start
 │
 ▼
Read discovery config
 │
 ▼
ForEach registered platform/object
 │
 ├── Run platform-specific discovery
 │
 ├── Write discovery object metadata
 │
 ├── Write discovery column metadata
 │
 └── Write discovery audit
 │
 ▼
Generate metadata inventory report
```

---

## 12. Metadata validation rules

### 12.1 Erwin export validation

| Rule | Severity |
|---|---|
| model_name is required | critical |
| model_version is required | critical |
| physical_object_name is required | critical |
| physical_column_name is required for column rows | critical |
| target_column_name is required for mapping rows | warning or critical |
| data_type is required | warning |
| duplicate physical object + column | critical |
| unsupported classification value | warning |

### 12.2 Platform discovery validation

| Rule | Severity |
|---|---|
| object exists | critical |
| column list can be extracted | critical |
| inferred schema is not empty | critical |
| file count > 0 | warning |
| unsupported data type | warning |

---

## 13. Output reports

### 13.1 Erwin ingestion report

Fields:

- model name
- model version
- export timestamp
- object count
- column count
- mapping count
- rejected row count
- warning count
- import status

### 13.2 Platform discovery report

Fields:

- discovery run id
- platform name
- object count
- column count
- file count
- schema inferred flag
- discovery status
- warning count

---

## 14. Deliverables

Phase 1A must produce:

- Erwin export specification
- sample Erwin export files for population dataset
- Erwin metadata landing structure
- Erwin staging table DDL
- model version table DDL
- platform discovery table DDL
- Erwin metadata ingestion notebook or pipeline
- platform metadata discovery notebook or pipeline
- metadata acquisition report

---

## 15. Acceptance criteria

Phase 1A is complete when:

- one Erwin export can be loaded into staging tables
- model version is captured
- Erwin object and column metadata are available
- source-to-target mapping rows can be captured where supplied
- one platform discovery job can capture physical metadata
- discovered metadata is stored in discovery tables
- metadata acquisition report is produced
- full reconciliation is explicitly deferred

---

## 16. Test scenarios

| Scenario | Expected result |
|---|---|
| Valid Erwin export | staging load succeeds |
| Missing model version | ingestion fails |
| Missing physical column name | row rejected or load fails |
| Duplicate column in export | validation error |
| Valid ADLS path | file profile created |
| Missing ADLS path | discovery failure logged |
| Valid Delta table | schema captured |
| Missing target table | discovery failure logged |

---

## 17. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Erwin export format varies | Define strict MVP export template |
| Modellers do not maintain source mappings | Allow partial mapping capture |
| Platform discovery differs by target | Use adapter pattern |
| Reconciliation starts too early | Keep Phase 1A as acquisition only |
| Metadata ownership unclear | Assign data modeller and data owner roles |
