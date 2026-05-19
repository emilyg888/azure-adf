# SPEC.md — Phase 0: Foundation

## 1. Phase objective

Establish the foundational architecture, repository scaffold, delivery conventions, metadata standards and operating model for the Metadata-Driven Azure/Fabric Data Ingestion and Transformation Framework.

This phase does not aim to build full runtime functionality. Its purpose is to create the structure that allows later phases to be delivered consistently.

---

## 2. Phase scope

### In scope

- Create project repository structure
- Define framework architecture baseline
- Define naming standards
- Define environment strategy
- Define metadata standards
- Define dataset onboarding template
- Define transformation contract template
- Define LLM coding agent guardrails
- Define review and approval principles
- Define MVP sample dataset
- Define initial backlog and delivery sequence
- Define framework package boundaries

### Out of scope

- Production CI/CD
- Full governance engine
- Full Erwin automated integration
- Full source-to-target reconciliation
- Multi-target production adapters
- Full operational monitoring
- Automated production deployment

---

## 3. Design principles

### 3.1 Separation of concerns

The framework must separate:

```text
Orchestration      → Fabric Pipeline
Metadata contract  → framework metadata tables / YAML contracts
Transformation     → Python / PySpark modules and notebook drivers
Target writing     → target adapters
Governance         → pluggable validation gates
Release control    → Azure DevOps later
```

### 3.2 Metadata-first delivery

Dataset-specific behaviour should be represented as metadata or contracts before it becomes code.

Examples:

- source path
- source format
- delimiter
- target platform
- target object
- write mode
- schema mapping
- transformation rule
- DQ rule
- PII rule
- lineage requirement

### 3.3 LLM coding agent is build-time only

The LLM coding agent may generate transformation code, tests and documentation.

It must not:

- run inside production pipeline to decide logic dynamically
- approve its own code
- deploy directly to production
- access secrets
- bypass tests or review

### 3.4 Human approval for material changes

Human review is mandatory for changes affecting:

- business rules
- source-to-target mappings
- PII handling
- DQ logic
- certified data products
- production target schema
- deduplication / merge logic
- regulatory or financial fields

---

## 4. Target repository scaffold

Create the following repository structure.

```text
azure-fabric-md-framework/
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
├── design/
│   ├── specs/
│   │   ├── phase_0_foundation_SPEC.md
│   │   ├── phase_1_metadata_ingestion_SPEC.md
│   │   ├── phase_1A_erwin_platform_metadata_SPEC.md
│   │   ├── phase_2_transformation_framework_SPEC.md
│   │   └── phase_4_partial_llm_agent_SPEC.md
│   │
│   └── decisions/
│       └── ADR-0001-framework-principles.md
│
├── fabric/
│   ├── pipelines/
│   ├── notebooks/
│   └── environments/
│       ├── dev.json
│       ├── test.json
│       └── prod.json
│
├── framework/
│   ├── metadata/
│   ├── ingestion/
│   ├── transforms/
│   ├── targets/
│   ├── governance/
│   └── audit/
│
├── metadata/
│   ├── ddl/
│   ├── seed/
│   └── contracts/
│
├── erwin/
│   ├── exports/
│   ├── model_ingestion/
│   └── mapping_templates/
│
├── agent/
│   ├── prompts/
│   ├── contracts/
│   └── generated_assets/
│
├── transforms/
│   └── pyspark/
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

## 5. Naming standards

### 5.1 Dataset identifiers

Pattern:

```text
DS_<DOMAIN>_<SUBJECT>_<SEQUENCE>
```

Examples:

```text
DS_REF_POPULATION_001
DS_CUST_PROFILE_001
DS_RISK_FRAUD_ALERT_001
```

### 5.2 Source system identifiers

Pattern:

```text
SRC_<PLATFORM>_<DOMAIN>_<SEQUENCE>
```

Examples:

```text
SRC_ADLS_REF_001
SRC_SYN_CUSTOMER_001
SRC_SNOWFLAKE_RISK_001
```

### 5.3 Target identifiers

Pattern:

```text
TGT_<PLATFORM>_<DOMAIN>_<SEQUENCE>
```

Examples:

```text
TGT_DELTA_REF_001
TGT_SNOWFLAKE_CORE_001
TGT_COSMOS_PROFILE_001
```

### 5.4 Pipeline names

Pattern:

```text
pl_<capability>_<purpose>
```

Examples:

```text
pl_metadata_driven_ingestion
pl_ingest_erwin_metadata
pl_platform_metadata_discovery
pl_generic_transform_driver
```

### 5.5 Notebook names

Pattern:

```text
nb_<capability>_<purpose>
```

Examples:

```text
nb_generic_transform_driver
nb_landing_validator
nb_erwin_export_loader
```

---

## 6. Environment strategy

### 6.1 Environment names

The framework should support:

```text
dev
test
prod
```

### 6.2 Environment config file

Create environment configuration files under:

```text
fabric/environments/
```

Example:

```json
{
  "environment": "dev",
  "metadata_database": "md_framework_dev",
  "raw_container": "raw",
  "processed_container": "processed",
  "lookup_container": "lookup",
  "audit_container": "audit",
  "default_target_platform": "delta",
  "key_vault_name": "kv-md-framework-dev"
}
```

### 6.3 Environment-specific values

These must not be hardcoded in notebooks or pipelines:

- storage account
- workspace id
- lakehouse id
- database name
- schema name
- service principal
- secret names
- connection names
- target platform endpoint
- Databricks workspace URL
- Snowflake account URL
- Cosmos endpoint

---

## 7. Baseline metadata standard

At Phase 0, define the initial metadata domains.

```text
md_source_system
md_dataset
md_dataset_source
md_dataset_target
md_schema_mapping
md_transformation_rule
md_governance_rule
md_pipeline_audit_log
md_coding_agent_task
md_generated_code_asset
```

Not every table must be physically implemented in Phase 0, but the shape and intent must be agreed.

---

## 8. Dataset onboarding template

Create:

```text
metadata/contracts/dataset_contract_template.yaml
```

Template:

```yaml
dataset_id: ""
dataset_name: ""
business_domain: ""
description: ""
data_owner: ""
data_steward: ""
load_type: "full"
frequency: "on_demand"

source:
  source_system_id: ""
  source_type: ""
  object_type: ""
  database: ""
  schema: ""
  object: ""
  path: ""
  format: ""
  delimiter: ""

target:
  target_platform: ""
  target_storage_type: ""
  target_format: ""
  database: ""
  schema: ""
  object: ""
  path: ""
  write_mode: ""
  write_strategy: ""

governance:
  dq_required: true
  pii_classification_required: false
  lineage_required: true
  certification_required: false
```

---

## 9. Transformation contract template

Create:

```text
metadata/contracts/transformation_contract_template.yaml
```

Template:

```yaml
dataset_id: ""
contract_version: "0.1"

inputs:
  - name: ""
    type: ""
    path: ""
    format: ""

lookups: []

outputs:
  - name: ""
    target_platform: ""
    target_object: ""

mappings:
  - source_column: ""
    target_column: ""
    target_data_type: ""
    nullable: true
    transformation_rule: ""

transformations:
  - sequence: 10
    name: ""
    type: ""
    expression: ""

tests:
  required:
    - schema_validation
    - row_count_check
    - mandatory_column_check
```

---

## 10. Coding standards

### 10.1 Python module style

- Use small reusable modules
- Avoid business logic inside pipeline definitions
- Avoid business logic directly embedded in notebook cells
- Prefer pure functions for transformations where possible
- Add docstrings for generated transformation functions
- Use explicit input and output DataFrames
- Avoid hardcoded paths
- Pass paths through metadata or parameters

### 10.2 Notebook style

Notebook should be a thin driver.

A notebook may:

- read parameters
- load metadata
- load source data
- call reusable transformation module
- call target writer
- call audit logger

A notebook should not:

- hold large business transformation logic directly
- hardcode storage account names
- hardcode production paths
- hardcode secrets
- define unreviewed DQ logic

---

## 11. Review and approval model

### 11.1 Change categories

| Change type | Review requirement |
|---|---|
| Documentation only | automated or peer review |
| Metadata-only non-production | peer review |
| Transformation logic | human review required |
| DQ rule | data owner / steward review |
| PII masking rule | governance / security review |
| Target schema change | architect / data modeller review |
| Production deployment | release approval |

### 11.2 Pull request evidence

A pull request should include:

- summary of change
- impacted dataset
- impacted source
- impacted target
- mapping changes
- test results
- generated code summary if LLM was used
- reviewer checklist
- approval decision

---

## 12. MVP sample dataset

Use the population-by-age dataset as the first sample dataset.

Reason:

- has raw file input
- has lookup input
- has cleansing logic
- has pivot logic
- has join logic
- has processed output
- is simple enough for MVP
- still demonstrates meaningful metadata-driven transformation

---

## 13. Deliverables

Phase 0 must produce:

- repository scaffold
- README.md
- architecture placeholder
- metadata model placeholder
- dataset contract template
- transformation contract template
- coding standards
- naming standards
- review model
- MVP sample dataset selection
- delivery backlog

---

## 14. Acceptance criteria

Phase 0 is complete when:

- repository structure exists
- baseline design docs exist
- naming standards are documented
- dataset contract template exists
- transformation contract template exists
- coding standards are documented
- approval principles are documented
- sample dataset is selected
- Phase 1 can begin without further structural decisions

---

## 15. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Framework becomes too broad too early | Lock MVP scope |
| Metadata model becomes over-engineered | Start with minimum viable metadata |
| Notebooks become hardcoded again | Enforce notebook driver pattern |
| LLM agent creates uncontrolled code | Require PR and approval |
| Environment config leaks into code | Use config files and Key Vault references |
