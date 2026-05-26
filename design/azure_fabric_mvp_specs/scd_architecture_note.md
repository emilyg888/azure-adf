# SCD Architecture Note

## Purpose

This note compares three Snowflake patterns for updating SCD target tables in the Element Fleet Services MVP/SIT design.

The three implemented patterns are:

- Procedural SQL SCD merge, used for `CONFORMED.DIM_CLIENT`.
- Snowflake stream-driven SCD merge, used for `CONFORMED.DIM_VEHICLE`.
- Dynamic-table-derived SCD, used for `CONFORMED.DIM_MAINTENANCE_VENDOR`.

## Pattern Comparison

| Pattern | How it works | Pros | Cons | Most suitable use cases | Current example |
|---|---|---|---|---|---|
| Procedural SQL SCD merge | Load latest eligible rows into a controlled `STG_FLEET` table, then run deterministic `UPDATE` to close changed current rows, `INSERT` to add new current rows, and optional soft-delete for missing full-extract keys. | Explicit and easy to audit; strongest control over transaction boundaries; works well for Type 2 dimensions with soft delete; easy to add foreign-key gating and DQ filters; familiar to warehouse teams. | More SQL to maintain; merge order matters; must be orchestrated carefully for day-by-day full extracts and deltas; repeated boilerplate across dimensions unless generated. | Core enterprise dimensions where correctness, auditability, and controlled recovery matter most; dimensions with parent-key checks; full extract plus mutable entity SCD2. | `CONFORMED.DIM_CLIENT` |
| Snowflake stream-driven SCD merge | Insert source rows into a controlled staging/load table; a Snowflake stream captures inserted rows; SCD merge logic consumes the stream into the target dimension. | Good for incremental change capture inside Snowflake; naturally separates load arrival from conformed consumption; supports task-based automation; avoids rescanning the full staging table for each run. | Streams track table changes, not business SCD semantics, so SCD logic is still required; stream consumption needs careful transaction handling; stream retention/staleness must be monitored; not ideal when the full source history must be recomputed. | Dimensions or facts loaded incrementally into Snowflake-controlled staging tables; event-style arrival patterns; pipelines that will later use Snowflake Tasks for orchestration. | `CONFORMED.DIM_VEHICLE` |
| Dynamic-table-derived SCD | Copy external/staged records into an internal history table, then define dynamic tables that derive eligible versions and SCD2 rows using window functions such as `LAG` and `LEAD`. | Declarative and compact; Snowflake manages refresh; excellent for small/medium reference dimensions; easy to inspect lineage from source history to conformed rows; reduces procedural merge code. | Dynamic tables cannot read external tables directly, so an internal history table is required; less suitable for complex soft-delete semantics unless snapshot completeness is carefully modelled; refresh behavior and cost need monitoring; surrogate keys from window functions may not be stable if historical ordering changes. | Small or medium reference dimensions with complete staged history; dimensions where the target can be derived from source version history; low operational complexity use cases. | `CONFORMED.DIM_MAINTENANCE_VENDOR` |

## Recommended Selection Rule

| Requirement | Recommended pattern |
|---|---|
| Strict SCD2 with soft delete from authoritative full extracts | Procedural SQL SCD merge |
| Incremental controlled Snowflake staging with task/stream orchestration | Snowflake stream-driven SCD merge |
| Small reference dimension derived from complete staged history | Dynamic-table-derived SCD |
| Parent foreign-key checks must block current-row creation | Procedural SQL merge or stream-driven merge |
| Need to replay and rebuild SCD target from retained history | Dynamic-table-derived SCD or full-refresh procedural merge |
| High audit and rollback requirements | Procedural SQL SCD merge |

## Design Guidance

For the MVP, keep deterministic conformed modelling in Snowflake SQL. ADLS STAGING can mark `_is_latest_for_business_key`, `_latest_resolution_status`, `_is_exact_duplicate`, and DQ status, but Snowflake CONFORMED must still re-check these flags before creating current rows.

The default production pattern should be procedural SQL SCD merge for core dimensions. Use streams when source arrival is incremental and Snowflake Tasks will own orchestration. Use dynamic tables for low-risk reference dimensions where the conformed table is naturally derived from complete staged history.

Do not use dynamic tables directly over external ADLS tables. Snowflake requires a supported internal source, so land external data into a controlled internal `STG_FLEET` history/load table first.

## Element Fleet Recommendation

| Dimension | Preferred production pattern | Reason |
|---|---|---|
| `DIM_CLIENT` | Procedural SQL SCD merge | Core parent dimension; high audit value; soft-delete semantics matter. |
| `DIM_VEHICLE` | Stream-driven SCD merge or procedural SQL merge | High relationship value and likely incremental arrival; must resolve `CLIENT_SK`. |
| `DIM_MAINTENANCE_VENDOR` | Dynamic-table-derived SCD | Small reference dimension; no parent dependency; source history is easy to retain. |
| `DIM_FUEL_CARD` | Procedural SQL merge or stream-driven SCD merge | Depends on vehicle/client relationships and may have operational state changes. |
