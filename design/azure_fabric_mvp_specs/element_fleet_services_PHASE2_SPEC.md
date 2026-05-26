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

## 5. Design guardrails

- Do not promote a `FEATURES` table into `GOLD` unless it has a named business consumption pattern.
- Do not let BI tools query raw feature tables directly when certified metric definitions are required.
- Keep model/scoring lineage in `FEATURES`, including source conformed tables, feature job run id, model or rule version, score timestamp, and batch date.
- Keep business metric definitions in `SEMANTIC`, not scattered across dashboards.
- Reuse `CONFORMED` surrogate keys and business keys; do not re-key entities in `GOLD` or `FEATURES` unless a specific serving pattern requires it.
- Treat `SEMANTIC` as a stable contract. Changes to certified metric names, grain, or security rules require versioning or explicit migration.

## 6. Recommended wording

I would keep the MVP Snowflake model simple with `STG_FLEET`, `CONFORMED`, and `AUDIT`. For the next phase, I would add `GOLD`, `FEATURES`, and `SEMANTIC`. `GOLD` is the business-ready analytical layer, `FEATURES` is where Snowpark-derived feature engineering and scoring outputs live, and `SEMANTIC` is the governed consumption contract for metrics, certified views, security, and BI/AI access.
