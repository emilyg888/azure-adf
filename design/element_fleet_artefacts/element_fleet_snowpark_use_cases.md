# Six Snowpark Use Cases for Element Fleet Services MVP

## Purpose

This document defines six practical Snowpark use cases for the Element Fleet Services MVP data platform.

The design assumes the current pipeline architecture:

```text
ADLS RAW
  ↓
ADLS STAGING
  ↓
Snowflake STG_FLEET
  ↓
Snowflake CONFORMED
  ↓
Snowflake FEATURES / GOLD / SEMANTIC
```

Snowpark should **not** replace the core ingestion, staging, audit, or conformed modelling pattern.

Instead:

```text
ADLS = ingestion, raw evidence, source-shaped staging
Snowflake SQL = deterministic conformed modelling
Snowpark = feature engineering, scoring, anomaly detection, advanced analytics
```

The recommended pattern is to run Snowpark **after Snowflake CONFORMED**, where business keys, surrogate keys, referential checks, and current/history records have already been resolved.

---

## Layering Recommendation

| Layer | Purpose | Primary Technology |
|---|---|---|
| `ADLS RAW` | Immutable source archive | ADLS |
| `ADLS STAGING` | Typed Parquet, schema checks, duplicate checks, source versioning, lineage | Fabric Foundry / Python / Spark-style processing |
| `FLEET_MVP.STG_FLEET` | Snowflake external or transient staging inputs | Snowflake SQL |
| `FLEET_MVP.CONFORMED` | Business-aligned dimensions, facts, summaries, version history | Snowflake SQL |
| `FLEET_MVP.FEATURES` | Snowpark-derived features and scores | Snowpark Python |
| `FLEET_MVP.GOLD` | Business-ready analytical marts and aggregates | Snowflake SQL / Snowpark |
| `FLEET_MVP.SEMANTIC` | Certified metrics, governed views, access contracts | Snowflake views / semantic tooling |
| `FLEET_MVP.AUDIT` | Load audit, DQ evidence, reconciliation, run status | Snowflake SQL |

---

# 1. Predictive Maintenance Features

## Business Question

Which vehicles are showing early indicators of maintenance risk, downtime risk, or unusually high operating cost?

## Why Snowpark

Predictive maintenance requires rolling windows, lag calculations, threshold logic, feature creation, and potentially model scoring. This is where Python is more expressive than pure SQL.

## Input Tables

```text
CONFORMED.FACT_MAINTENANCE_WORK_ORDER
CONFORMED.FACT_TELEMATICS_DAILY_SUMMARY
CONFORMED.DIM_VEHICLE
CONFORMED.DIM_CLIENT
CONFORMED.FACT_LEASE_CONTRACT
```

## Output Table

```text
FEATURES.FEATURE_VEHICLE_MAINTENANCE_RISK
```

## Example Features

| Feature | Description |
|---|---|
| `days_since_last_service` | Days since last completed maintenance event |
| `maintenance_cost_90d` | Total maintenance cost over last 90 days |
| `repeat_repair_count_180d` | Count of repeat repairs over last 180 days |
| `cost_per_1000_km` | Maintenance cost normalised by usage |
| `high_odometer_growth_flag` | Vehicle usage growth exceeding expected pattern |
| `downtime_event_count` | Number of maintenance-related downtime events |
| `maintenance_risk_score` | Composite score for maintenance risk |

## Pipeline Pattern

```text
CONFORMED facts and dimensions
  ↓
Snowpark feature generation
  ↓
FEATURES.FEATURE_VEHICLE_MAINTENANCE_RISK
  ↓
GOLD maintenance risk dashboard / SEMANTIC certified view
```

## Value

- Supports proactive maintenance planning.
- Reduces unexpected downtime.
- Improves supplier and vehicle model performance visibility.
- Creates a foundation for future ML-based failure prediction.

---

# 2. Fuel Anomaly Detection

## Business Question

Which fuel transactions look unusual when compared with vehicle usage, location, fuel card history, or normal fleet behaviour?

## Why Snowpark

Fuel anomaly detection benefits from rolling statistics, behavioural baselines, outlier detection, and multi-source feature engineering. Snowpark allows this logic to run close to Snowflake data without exporting large datasets.

## Input Tables

```text
CONFORMED.FACT_FUEL_TRANSACTION
CONFORMED.FACT_TELEMATICS_DAILY_SUMMARY
CONFORMED.DIM_FUEL_CARD
CONFORMED.DIM_VEHICLE
CONFORMED.DIM_CLIENT
```

## Output Table

```text
FEATURES.FEATURE_FUEL_ANOMALY_SCORE
```

## Example Features

| Feature | Description |
|---|---|
| `fuel_cost_per_km` | Fuel spend normalised by vehicle usage |
| `transaction_frequency_7d` | Number of fuel transactions in rolling 7-day window |
| `multiple_fill_flag` | Multiple fuel events within short time period |
| `no_usage_match_flag` | Fuel event without matching recent vehicle usage |
| `high_value_transaction_flag` | Transaction materially above normal pattern |
| `fuel_card_vehicle_mismatch_flag` | Fuel card activity inconsistent with assigned vehicle |
| `fuel_anomaly_score` | Composite anomaly score |

## Pipeline Pattern

```text
Fuel transactions + telematics summaries
  ↓
Snowpark anomaly feature logic
  ↓
FEATURES.FEATURE_FUEL_ANOMALY_SCORE
  ↓
GOLD fuel exception monitoring / SEMANTIC certified anomaly view
```

## Value

- Identifies possible misuse, fraud, data errors, or card control issues.
- Supports exception management.
- Provides a strong practical Snowpark use case without requiring full ML maturity.

---

# 3. Vehicle / Driver-App Behaviour Scoring

## Business Question

Which vehicles, clients, or driver-app activity patterns indicate higher safety risk, usage risk, or engagement issues?

## Design Note

The current MVP does not include a standalone driver master. Driver app data should therefore be modelled as **vehicle/client-linked behaviour**, not true driver-level scoring.

If a future `DIM_DRIVER` is introduced, this use case can be extended to driver-level analytics.

## Why Snowpark

Behaviour scoring often requires event aggregation, normalisation, weighting, and feature scoring across multiple behavioural indicators. Snowpark is well suited to this style of Python-based feature engineering.

## Input Tables

```text
CONFORMED.FACT_DRIVER_APP_DAILY_SUMMARY
CONFORMED.FACT_TELEMATICS_DAILY_SUMMARY
CONFORMED.DIM_VEHICLE
CONFORMED.DIM_CLIENT
```

## Output Table

```text
FEATURES.FEATURE_VEHICLE_DRIVER_APP_BEHAVIOUR
```

## Example Features

| Feature | Description |
|---|---|
| `app_event_count_7d` | Driver app activity count over last 7 days |
| `safety_event_count_30d` | Count of safety-related app or telematics events |
| `harsh_event_rate` | Harsh braking, acceleration, or cornering rate if available |
| `low_engagement_flag` | Expected app activity missing or below threshold |
| `usage_intensity_score` | Composite score based on vehicle usage and app behaviour |
| `behaviour_risk_score` | Composite behaviour risk indicator |

## Pipeline Pattern

```text
Driver app summaries + telematics summaries
  ↓
Snowpark behaviour feature engineering
  ↓
FEATURES.FEATURE_VEHICLE_DRIVER_APP_BEHAVIOUR
  ↓
GOLD vehicle behaviour monitoring / SEMANTIC client fleet insights
```

## Value

- Supports client fleet safety monitoring.
- Highlights usage and engagement anomalies.
- Creates a future bridge to driver-level analytics if driver identity becomes available.

---

# 4. EV Charging and Reimbursement Analytics

## Business Question

Are EV charging sessions and reimbursement patterns reasonable, cost-effective, and aligned to vehicle usage?

## Why Snowpark

EV analytics often requires normalisation across kWh, cost, location type, reimbursement timing, vehicle usage, and expected charging patterns. Snowpark can generate reusable features and flags for exception monitoring.

## Input Tables

```text
CONFORMED.FACT_EV_CHARGING_SESSION
CONFORMED.FACT_TELEMATICS_DAILY_SUMMARY
CONFORMED.DIM_VEHICLE
CONFORMED.DIM_CLIENT
CONFORMED.FACT_LEASE_CONTRACT
```

## Output Table

```text
FEATURES.FEATURE_EV_CHARGING_BEHAVIOUR
```

## Example Features

| Feature | Description |
|---|---|
| `cost_per_kwh` | Charging cost normalised by energy consumed |
| `charging_sessions_30d` | Number of sessions in rolling 30-day period |
| `public_vs_home_charging_ratio` | Share of charging by charging location type, if available |
| `reimbursement_lag_days` | Days between charging event and reimbursement |
| `high_cost_session_flag` | Session cost outside expected range |
| `low_usage_high_charging_flag` | Charging volume inconsistent with vehicle usage |
| `ev_charging_exception_score` | Composite score for charging/reimbursement exceptions |

## Pipeline Pattern

```text
EV charging sessions + vehicle usage summaries
  ↓
Snowpark feature generation and exception scoring
  ↓
FEATURES.FEATURE_EV_CHARGING_BEHAVIOUR
  ↓
GOLD EV cost and reimbursement dashboard
```

## Value

- Supports fleet electrification governance.
- Helps identify abnormal reimbursement claims.
- Enables client reporting for EV cost and utilisation.
- Provides a useful future input into sustainability analytics.

---

# 5. Supplier Performance Scoring

## Business Question

Which maintenance vendors are delivering good value, reliable service, and acceptable turnaround times?

## Why Snowpark

Supplier scoring often requires composite scoring, normalisation by vehicle type, repeat-repair detection, cost variance, and rolling performance trends. Snowpark is useful for implementing transparent, configurable scoring logic.

## Input Tables

```text
CONFORMED.FACT_MAINTENANCE_WORK_ORDER
CONFORMED.DIM_SUPPLIER
CONFORMED.DIM_VEHICLE
CONFORMED.DIM_CLIENT
CONFORMED.FACT_INSURANCE_CLAIM
```

## Output Table

```text
FEATURES.FEATURE_SUPPLIER_PERFORMANCE_SCORE
```

## Example Features

| Feature | Description |
|---|---|
| `avg_repair_cost_90d` | Average repair cost over last 90 days |
| `median_cycle_time_days` | Median maintenance cycle time |
| `repeat_repair_rate` | Share of work orders followed by repeat repair |
| `cost_variance_by_vehicle_class` | Cost deviation from peer vendor baseline |
| `claim_after_service_rate` | Insurance or incident events following service, where applicable |
| `supplier_performance_score` | Composite vendor score |

## Pipeline Pattern

```text
Maintenance work orders + supplier dimension
  ↓
Snowpark supplier feature generation
  ↓
FEATURES.FEATURE_SUPPLIER_PERFORMANCE_SCORE
  ↓
GOLD supplier scorecard / SEMANTIC vendor performance view
```

## Value

- Helps manage vendor networks.
- Supports procurement and operational improvement.
- Identifies suppliers with abnormal cost, quality, or cycle-time patterns.
- Provides business-facing scorecards for fleet operations.

---

# 6. Total Cost of Ownership Features

## Business Question

What is the true total cost of ownership by vehicle, client, fleet segment, or lease period?

## Why Snowpark

Total Cost of Ownership can begin as SQL aggregation, but Snowpark becomes valuable when the cost logic includes allocation, normalisation, exception handling, depreciation/residual-value modelling, and scenario features.

## Input Tables

```text
CONFORMED.FACT_LEASE_CONTRACT
CONFORMED.FACT_MAINTENANCE_WORK_ORDER
CONFORMED.FACT_FUEL_TRANSACTION
CONFORMED.FACT_EV_CHARGING_SESSION
CONFORMED.FACT_INSURANCE_CLAIM
CONFORMED.FACT_REGISTRATION_EVENT
CONFORMED.FACT_BILLING_INVOICE
CONFORMED.FACT_REMARKETING_AUCTION_RESULT
CONFORMED.DIM_VEHICLE
CONFORMED.DIM_CLIENT
```

## Output Tables

```text
GOLD.GOLD_VEHICLE_TCO_MONTHLY
GOLD.GOLD_CLIENT_FLEET_TCO_MONTHLY
FEATURES.FEATURE_VEHICLE_TCO_PROFILE
```

## Example Metrics and Features

| Metric / Feature | Description |
|---|---|
| `lease_cost_monthly` | Monthly lease or financing cost |
| `maintenance_cost_monthly` | Monthly maintenance cost |
| `fuel_or_energy_cost_monthly` | Fuel and EV charging cost |
| `claims_cost_monthly` | Insurance and claims cost |
| `registration_cost_monthly` | Registration and compliance-related cost |
| `remarketing_recovery_amount` | Resale or disposal recovery |
| `tco_monthly` | Total cost of ownership for the month |
| `tco_per_km` | Cost normalised by usage |
| `residual_value_gap` | Difference between expected and actual remarketing outcome |
| `high_tco_flag` | Vehicle/client segment materially above expected cost |

## Pipeline Pattern

```text
Conformed lifecycle facts
  ↓
Snowpark cost normalisation and feature generation
  ↓
FEATURES.FEATURE_VEHICLE_TCO_PROFILE
  ↓
GOLD.GOLD_VEHICLE_TCO_MONTHLY
  ↓
SEMANTIC certified TCO metrics
```

## Value

- Creates one of the highest-value fleet analytics products.
- Supports client advisory, pricing, fleet optimisation, and retention.
- Connects leasing, operations, maintenance, fuel, EV, claims, and remarketing into one business outcome.
- Provides a strong foundation for AI copilot and executive reporting.

---

## Recommended Implementation Sequence

Do not implement all six use cases at once.

Recommended sequence:

| Phase | Use Case | Reason |
|---|---|---|
| 1 | Total Cost of Ownership Features | Highest business value and strongest fleet-management narrative |
| 2 | Supplier Performance Scoring | Direct operational improvement use case |
| 3 | Fuel Anomaly Detection | Strong control and exception-monitoring use case |
| 4 | Predictive Maintenance Features | High value but depends on stronger historical data |
| 5 | EV Charging and Reimbursement Analytics | Strong future-facing EV use case |
| 6 | Vehicle / Driver-App Behaviour Scoring | Useful, but driver-level value depends on future driver master data |

---

## Design Principles

1. **Do not use Snowpark for basic ELT that SQL can handle cleanly.**

   Use SQL for deterministic joins, merges, SCD2 dimensions, fact loading, and simple aggregations.

2. **Use Snowpark where Python adds material value.**

   Good examples include rolling features, scoring, anomaly detection, reusable Python functions, and future ML model scoring.

3. **Keep CONFORMED clean.**

   CONFORMED should remain the reusable enterprise model. Snowpark-derived scores and analytical features should land in `FEATURES` or `GOLD`, not directly into `CONFORMED`.

4. **Separate features from certified metrics.**

   `FEATURES` can contain experimental or model-oriented signals. `SEMANTIC` should expose certified business definitions and governed consumption views.

5. **Preserve auditability.**

   Every Snowpark job should write job run metadata, input row counts, output row counts, scoring version, feature version, and exception counts into `AUDIT`.

6. **Version scoring logic.**

   Snowpark feature jobs should carry a `feature_version`, `scoring_version`, or `ruleset_version` so outputs can be explained and reproduced.

---

## Proposed Snowflake Schemas

```text
FLEET_MVP.STG_FLEET
FLEET_MVP.CONFORMED
FLEET_MVP.FEATURES
FLEET_MVP.GOLD
FLEET_MVP.SEMANTIC
FLEET_MVP.AUDIT
```

## Summary

A concise explanation:

> I would not use Snowpark as a replacement for the core data pipeline. ADLS remains the raw and staging evidence layer, and Snowflake SQL handles deterministic conformed modelling. Snowpark is best introduced after CONFORMED, where the data has business keys, referential integrity, current/history handling, and reliable grains. I would use Snowpark for predictive maintenance features, fuel anomaly detection, vehicle/app behaviour scoring, EV charging analytics, supplier scoring, and total cost of ownership features. These outputs should land in FEATURES or GOLD, and then be exposed through SEMANTIC views where they become certified, governed business insights.
