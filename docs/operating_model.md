# Operating Model

## Roles

| Role | Responsibilities |
|---|---|
| Data owner | Approves business meaning, access intent, and certification decisions |
| Data steward | Reviews DQ rules, definitions, lineage, and data classification |
| Data modeller | Owns Erwin model exports and source-to-target mapping intent |
| Data engineer | Implements and tests ingestion, transformation, and target write behaviour |
| Platform engineer | Owns environment configuration, connections, infrastructure, and CI/CD |
| Reviewer | Reviews material changes before runtime use |

## Review Triggers

Human review is required for business rules, PII handling, DQ logic, certified outputs, target schema changes, deduplication, joins, financial/regulatory fields, and generated code promotion.

## Support Model

MVP run evidence is written as local audit JSONL files. Fabric/ADF operational monitoring can consume equivalent status records once deployed.
