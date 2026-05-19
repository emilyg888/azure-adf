# Governance Design

Governance is implemented as pluggable gates around ingestion, transformation, and publication.

## MVP Gates

| Gate | Phase | Behaviour |
|---|---|---|
| Metadata completeness | 1 | Required source/target fields must exist before ingestion |
| Landing validation | 1 | Target path/file exists and row count evidence is captured |
| Erwin export validation | 1A | Required model/object/column fields are validated |
| Platform discovery validation | 1A | File/object/schema metadata is captured |
| Transformation schema validation | 2 | Output columns must match the contract expectation |
| Agent review checklist | 4 partial | Generated code cannot self-approve |

## Evidence

Run evidence should include dataset id, run id, phase, status, row counts, warning count, error message, code version, metadata version, and contract version where applicable.
