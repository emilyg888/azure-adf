# SPEC_PHASE2.md — Element Fleet Services Gold, Features, and Semantic Extensions

## 1. Phase-two objective

Extend the MVP Snowflake model after clear consumption patterns are defined. The MVP remains limited to `STG_FLEET`, `CONFORMED`, and `AUDIT`. Phase two adds `GOLD`, `FEATURES`, and `SEMANTIC` as separate consumption-oriented schemas.

Recommended positioning:

```text
ADLS RAW
  ↓
ADLS STAGING
  ↓
Snowflake STG_FLEET
  ↓
Snowflake CONFORMED
  ↓
Snowflake GOLD
  ↓
Snowflake SEMANTIC
```

`GOLD` and `SEMANTIC` are intentionally excluded from the MVP design because the reporting and consumption contracts are not yet defined.

For Snowpark-derived outputs:

```text
Snowflake CONFORMED
  ↓
Snowpark jobs
  ↓
Snowflake FEATURES
  ↓
GOLD / SEMANTIC / ML / AI consumption
```

## 2. Schema responsibilities

| Schema | Responsibility | Phase-two rule |
|---|---|---|
| `GOLD` | business-ready analytical aggregates for reporting | build only when a defined reporting or monitoring use case exists |
| `FEATURES` | Snowpark-derived model inputs, scoring outputs, anomaly signals, and reusable analytical features | do not mix with reporting aggregates unless the output is explicitly business-facing |
| `SEMANTIC` | governed consumption contract for metrics, certified views, row/column security, and BI/AI access | expose stable, named views and metrics over `GOLD`, `FEATURES`, and selected `CONFORMED` tables |

One important rule:

```text
GOLD != all Snowpark outputs
```

Use this split:

- `GOLD` is for business aggregates used by reporting and monitoring.
- `FEATURES` is for model, scoring, and analytical-signal inputs or outputs.
- `SEMANTIC` is for governed consumption contracts.

## 3. Snowpark output pattern

Snowpark jobs should read from `CONFORMED`, not from RAW files or uncontrolled external files. Outputs should land in `FEATURES` when they are model/scoring-oriented and in `GOLD` only when they are business-ready aggregates.

Example flow:

```text
CONFORMED.FACT_FUEL_TRANSACTION
CONFORMED.FACT_TELEMATICS_DAILY_SUMMARY
        ↓
FEATURES.FEATURE_FUEL_ANOMALY_SCORE
        ↓
GOLD.GOLD_FUEL_ANOMALY_DAILY
        ↓
SEMANTIC.SEMANTIC_FUEL_ANOMALY_MONITORING
```

## 4. Example phase-two objects

| Object | Layer | Purpose |
|---|---|---|
| `FEATURES.FEATURE_FUEL_ANOMALY_SCORE` | `FEATURES` | vehicle, client, fuel-card, and date-level anomaly score produced by Snowpark |
| `FEATURES.FEATURE_TELEMATICS_RISK_SIGNAL` | `FEATURES` | reusable risk features from telematics summaries |
| `GOLD.GOLD_FUEL_ANOMALY_DAILY` | `GOLD` | business-facing daily anomaly monitoring aggregate |
| `GOLD.GOLD_FLEET_UTILISATION_MONTHLY` | `GOLD` | monthly utilisation reporting aggregate |
| `SEMANTIC.SEMANTIC_FUEL_ANOMALY_MONITORING` | `SEMANTIC` | governed BI/AI access view over certified anomaly metrics |
| `SEMANTIC.SEMANTIC_FLEET_OPERATIONS` | `SEMANTIC` | governed fleet operations consumption contract |

## 5. Fuel Anomaly Detection Feature MVP

### Objective

Build use case 2 from the Snowpark use-case note as a FEATURES-layer MVP only. The output is `FEATURES.FEATURE_FUEL_ANOMALY_SCORE`. No `GOLD` aggregate or `SEMANTIC` consumption view is created until monitoring requirements, metric definitions, and access contracts are agreed.

### Input Tables

The Snowpark job reads from conformed Snowflake objects only:

```text
CONFORMED.FACT_FUEL_TRANSACTION
CONFORMED.FACT_TELEMATICS_DAILY_SUMMARY
CONFORMED.DIM_FUEL_CARD
CONFORMED.DIM_VEHICLE
CONFORMED.DIM_CLIENT
```

### Output Table

```text
FEATURES.FEATURE_FUEL_ANOMALY_SCORE
```

Target grain:

```text
one row per fuel_transaction_id scoring run
```

### Feature Columns

| Column | Purpose |
|---|---|
| `fuel_transaction_id` | source transaction being scored |
| `fuel_card_id`, `vehicle_id`, `client_id` | business keys for investigation and joining |
| `vehicle_sk`, `client_sk` | conformed surrogate keys where available |
| `transaction_datetime`, `transaction_date` | event time and scoring date |
| `litres`, `gross_amount`, `distance_km` | base transaction and usage measures |
| `fuel_cost_per_km` | spend normalised by same-day vehicle distance |
| `transaction_frequency_7d` | rolling 7-day card transaction count |
| `multiple_fill_flag` | repeated fuel activity in the 7-day card window |
| `no_usage_match_flag` | transaction has no same-day telematics usage match |
| `high_value_transaction_flag` | transaction is over threshold or materially above card baseline |
| `fuel_card_vehicle_mismatch_flag` | card assignment conflicts with transaction vehicle/client |
| `fuel_anomaly_score` | rule-based score from 0 to 100 |
| `anomaly_reason_codes` | comma-separated reason codes for explainability |
| `feature_version`, `scored_at`, `batch_date` | feature lineage |

### Scoring Rules

| Signal | Score contribution |
|---|---:|
| High value transaction | 30 |
| No matching vehicle usage | 25 |
| Fuel card vehicle/client mismatch | 30 |
| Multiple fills in rolling 7-day window | 15 |

The MVP score is capped at 100. It is intentionally rules-based and explainable; no ML model is required for this phase.

### Deployment Artifacts

| Artifact | Purpose |
|---|---|
| `snowpark/element_fleet/fuel_anomaly_feature.py` | Snowpark Python implementation for feature generation |
| `metadata/ddl/element_fleet_features_fuel_anomaly.sql` | Snowflake FEATURES table, Python stored procedure, and feature audit checks |

### Execution Pattern

```text
CONFORMED fuel, telematics, vehicle, client, fuel-card tables
        ↓
Snowpark feature generation
        ↓
FEATURES.FEATURE_FUEL_ANOMALY_SCORE
```

Example execution:

```sql
CALL FEATURES.BUILD_FEATURE_FUEL_ANOMALY_SCORE('2026-05-26');
```

### MVP Acceptance Criteria

| Check | Expected result |
|---|---|
| Feature table exists in `FEATURES` | `FEATURES.FEATURE_FUEL_ANOMALY_SCORE` is queryable |
| Row count | one feature row per fuel transaction in the scored conformed set |
| Score range | every `fuel_anomaly_score` is between 0 and 100 |
| Explainability | flagged rows include `anomaly_reason_codes` |
| Scope control | no `GOLD` or `SEMANTIC` fuel anomaly objects are created by this MVP artifact |

## 6. Design guardrails

- Do not promote a `FEATURES` table into `GOLD` unless it has a named business consumption pattern.
- Do not let BI tools query raw feature tables directly when certified metric definitions are required.
- Keep model/scoring lineage in `FEATURES`, including source conformed tables, feature job run id, model or rule version, score timestamp, and batch date.
- Keep business metric definitions in `SEMANTIC`, not scattered across dashboards.
- Reuse `CONFORMED` surrogate keys and business keys; do not re-key entities in `GOLD` or `FEATURES` unless a specific serving pattern requires it.
- Treat `SEMANTIC` as a stable contract. Changes to certified metric names, grain, or security rules require versioning or explicit migration.

## 7. Recommended wording

I would keep the MVP Snowflake model simple with `STG_FLEET`, `CONFORMED`, and `AUDIT`. For the next phase, I would add `GOLD`, `FEATURES`, and `SEMANTIC`. `GOLD` is the business-ready analytical layer, `FEATURES` is where Snowpark-derived feature engineering and scoring outputs live, and `SEMANTIC` is the governed consumption contract for metrics, certified views, security, and BI/AI access.
