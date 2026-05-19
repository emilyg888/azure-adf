# Metadata Model

## Core Entities

| Entity | Purpose |
|---|---|
| `md_source_system` | Registered source platforms and connection references |
| `md_dataset` | Business dataset registration independent of physical layout |
| `md_dataset_source` | Source contract: object, path, format, delimiter, and incremental settings |
| `md_dataset_target` | Target contract: platform, object/path, format, mode, and strategy |
| `md_schema_mapping` | Source-to-target column mapping with business definition and rule linkage |
| `md_transformation_rule` | Ordered deterministic transformation steps |
| `md_governance_rule` | DQ, PII, lineage, and certification rules |
| `md_pipeline_audit_log` | Runtime status, counts, warnings, and errors |
| `md_coding_agent_task` | Build-time agent task tracking |
| `md_generated_code_asset` | Generated asset inventory and review state |

## Lifecycle

1. Dataset owner registers dataset and source details.
2. Data modeller or engineer defines source, target, mapping, and transformation contracts.
3. Framework validates metadata completeness before runtime.
4. Runtime components read active metadata only.
5. Audit events capture run evidence and contract/code versions.
