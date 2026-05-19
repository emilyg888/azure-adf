# Package Boundaries

## `framework.metadata`

Owns metadata and contract loading, validation, and lookup concerns. This package must not copy data, write targets, or embed dataset business logic.

## `framework.ingestion`

Owns source-to-landing movement and landing validation. This package reads metadata contracts and delegates audit logging to `framework.audit`.

## `framework.transforms`

Owns reusable transformation orchestration, rule execution, and registry lookup. Dataset-specific transformation logic belongs under `transforms/`.

## `framework.targets`

Owns target writer interfaces and platform-specific adapters. Target writers must receive target contracts instead of hardcoded paths.

## `framework.governance`

Owns data quality, PII, lineage, and certification checks. Phase 0-2 keep this package intentionally lightweight.

## `framework.audit`

Owns run evidence and audit event persistence. Runtime code should log status transitions through this package.
