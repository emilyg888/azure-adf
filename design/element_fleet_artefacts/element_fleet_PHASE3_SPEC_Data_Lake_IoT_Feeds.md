# PHASE3_SPEC.md — Data Lake Pipelines for IoT-Like Fleet Data Feeds

## 1. Delivery Objective

Phase 3 extends the Element Fleet Services MVP into an **AI-ready Data Lake pipeline architecture** for high-volume, IoT-like data feeds.

The objective is to support fleet-management use cases where event data is generated continuously or frequently from:

- telematics providers
- vehicle diagnostics systems
- driver app events
- EV charging systems
- fuel-card and odometer feeds
- CRM / client portal events
- maintenance workflow updates
- future connected-vehicle APIs

Phase 3 focuses on building an open, replayable, governed Data Lake foundation that can support:

```text
IoT-like event ingestion
  ↓
validated event landing
  ↓
curated event stores
  ↓
feature and signal generation
  ↓
AI-ready semantic consumption
```

The key architectural shift is:

```text
MVP:
ADLS RAW → ADLS STAGING → Snowflake CONFORMED

Phase 3:
ADLS RAW → ADLS STAGING → Data Lake OPEN CURATED → FEATURES / SIGNALS → SEMANTIC AI consumption
```

Snowflake can still be used as a governed serving layer for conformed dimensions, gold marts, semantic views, and trusted AI/BI access. Phase 3 does not require an all-Snowflake or all-lakehouse design.

---

## 2. Phase 3 Scope

### In Scope

- Define Data Lake pipeline architecture for IoT-like event feeds.
- Add open curated event-store layers in ADLS.
- Support batch and micro-batch ingestion patterns.
- Support future streaming ingestion patterns.
- Standardise event envelope metadata.
- Store high-volume event data in Parquet / Delta / Iceberg-compatible formats.
- Build curated event tables for telematics, driver app events, EV charging, CRM portal events, and diagnostics.
- Generate AI-ready feature tables.
- Generate governed signal tables.
- Add feature and signal registries.
- Add event-level audit and replay capability.
- Add data quality, schema drift, deduplication, watermarking, and late-arrival handling.
- Define integration boundaries with Snowflake CONFORMED, GOLD, SEMANTIC, and AUDIT schemas.
- Define AI consumption contracts.

### Out of Scope

- Full real-time production streaming implementation.
- Production telematics vendor integration.
- Real driver identity resolution.
- Production ML model training.
- Automated decisioning.
- Real-time driver scoring for HR or disciplinary use.
- Production personal data policy implementation.
- Full enterprise MDM implementation.
- Full feature store product selection.

---

## 3. Design Principles

## 3.1 AI Does Not Mean Raw Data Access

AI should not freely consume uncontrolled raw or staging event data.

```text
Wrong:
AI → RAW events

Right:
AI → certified semantic views
AI → governed feature tables
AI → registered signal tables
AI → retrieval-ready metadata
AI → audit evidence
```

## 3.2 Lower Layers Should Be Open

High-volume event data should be stored in open formats:

```text
Parquet
Delta
Iceberg-compatible tables where available
```

This improves portability across:

- Databricks
- Microsoft Fabric
- Snowflake external tables
- Spark
- Trino / Presto
- future AI and ML platforms

## 3.3 Upper Layers Should Be Governed

Conformed, Gold, Semantic, Feature, and Signal layers require stronger governance:

- ownership
- data quality thresholds
- lineage
- access control
- sensitivity classification
- certified definitions
- feature / signal versioning
- AI-safe consumption flags

## 3.4 Event Data Should Be Replayable

All event pipelines must support replay from durable lake storage.

```text
RAW event payload
  ↓
STAGING typed event
  ↓
OPEN CURATED event table
  ↓
FEATURES / SIGNALS
```

Reprocessing must not corrupt existing curated or feature outputs.

## 3.5 Signals Are Not Raw Events

Signals are derived, governed indicators.

Example:

```text
raw fuel transaction
+ vehicle usage
+ odometer pattern
+ fuel-card assignment
= SIGNAL_FUEL_ANOMALY
```

Signals must be versioned, explainable, and auditable.

---

## 4. Target Architecture

```text
Source Systems / APIs / Event Feeds
        ↓
Ingestion Gateway
Batch, micro-batch, future streaming
        ↓
ADLS RAW_EVENTS
Original event payload, immutable archive
        ↓
ADLS STAGED_EVENTS
Typed, validated, deduplicated event records
        ↓
ADLS OPEN_CURATED_EVENTS
Reusable event-store tables
        ↓
FEATURE PIPELINES
Rolling windows, aggregations, feature engineering
        ↓
SIGNAL PIPELINES
Risk flags, anomaly indicators, explainable scores
        ↓
Snowflake / Lakehouse FEATURES and SIGNALS
Governed AI-ready feature and signal tables
        ↓
GOLD / SEMANTIC
Certified business metrics, views, and contracts
        ↓
AI / BI / ML / APIs / Copilots
```

---

## 5. Recommended Platform Boundary

| Layer | Recommended Platform | Purpose |
|---|---|---|
| `RAW_EVENTS` | ADLS | Immutable source payloads |
| `STAGED_EVENTS` | ADLS Parquet | Typed, validated, source-shaped events |
| `OPEN_CURATED_EVENTS` | ADLS / Lakehouse | Reusable event store |
| `FEATURES` | Lakehouse and/or Snowpark | AI/ML feature engineering |
| `SIGNALS` | Lakehouse and/or Snowflake | Governed, explainable indicators |
| `CONFORMED` | Snowflake or governed lakehouse | Business entities, facts, dimensions |
| `GOLD` | Snowflake / Fabric / governed serving layer | Business-ready marts |
| `SEMANTIC` | Snowflake / Fabric semantic model / catalog | Certified AI and BI access |
| `AUDIT` | ADLS + Snowflake | Durable evidence and queryable audit |

---

## 6. Data Lake Zones

## 6.1 RAW_EVENTS

Purpose:

- Preserve the original payload exactly as received.
- Support replay, audit, and source traceability.
- Avoid destructive updates.

Path pattern:

```text
abfss://raw@<storage-account>.dfs.core.windows.net/
  domain=fleet_management/
  source_system=<source_system_id>/
  feed=<feed_name>/
  event_date=YYYY-MM-DD/
  event_hour=HH/
  ingest_run_id=<run_id>/
  <original_file_or_payload>
```

Accepted formats:

| Format | Usage |
|---|---|
| JSON | API/event payloads |
| CSV | vendor batch feeds |
| Avro | future streaming or schema-registry feeds |
| Parquet | vendor analytical exports |
| Binary/raw payload | exceptional audit retention |

RAW rules:

- append-only
- no parsing
- no type coercion
- no deduplication
- no business logic
- retain source headers and metadata where possible

---

## 6.2 STAGED_EVENTS

Purpose:

- Convert raw event payloads into typed, validated, source-shaped Parquet tables.
- Preserve event identity and ingestion lineage.
- Detect duplicates and malformed records.

Path pattern:

```text
abfss://staging@<storage-account>.dfs.core.windows.net/
  domain=fleet_management/
  feed=<feed_name>/
  batch_date=YYYY-MM-DD/
  event_hour=HH/
  part-*.parquet
```

Required staging columns:

| Column | Purpose |
|---|---|
| `_source_system_id` | Source system identifier |
| `_feed_id` | Event feed identifier |
| `_source_file_name` | Source file name where applicable |
| `_source_file_path` | Raw source path |
| `_source_event_id` | Event identifier from source where available |
| `_event_business_key` | Canonical event key |
| `_event_timestamp` | Event occurrence timestamp |
| `_event_date` | Derived event date |
| `_ingest_timestamp` | Platform receipt timestamp |
| `_ingest_run_id` | Pipeline run identifier |
| `_source_sequence_number` | Optional event sequence from source |
| `_payload_hash` | Hash of source payload |
| `_schema_version` | Source schema version |
| `_is_exact_duplicate` | Duplicate payload indicator |
| `_dq_status` | passed, warning, rejected |
| `_reject_reason` | Reason for rejected or quarantined record |
| `_late_arrival_flag` | Whether event arrived after expected window |
| `_processing_watermark` | Pipeline watermark used for processing |

---

## 6.3 OPEN_CURATED_EVENTS

Purpose:

- Provide reusable, clean, queryable event-store tables.
- Support feature engineering and AI/ML workloads.
- Keep high-volume event history open and portable.

Recommended formats:

```text
Delta or Iceberg-compatible table format
Parquet physical storage
```

Example tables:

```text
OPEN_CURATED_EVENTS.TELEMATICS_DAILY_EVENT
OPEN_CURATED_EVENTS.TELEMATICS_GPS_EVENT
OPEN_CURATED_EVENTS.VEHICLE_DIAGNOSTIC_EVENT
OPEN_CURATED_EVENTS.DRIVER_APP_EVENT
OPEN_CURATED_EVENTS.EV_CHARGING_EVENT
OPEN_CURATED_EVENTS.CLIENT_PORTAL_EVENT
OPEN_CURATED_EVENTS.FUEL_CARD_EVENT
```

Partitioning guidance:

| Feed | Recommended Partitioning |
|---|---|
| Telematics GPS | event_date, provider_id, vehicle_id hash bucket |
| Diagnostics | event_date, diagnostic_type |
| Driver app | event_date, app_platform, event_type |
| EV charging | event_date, charging_provider |
| Client portal | event_date, channel, event_type |
| Fuel events | transaction_date, fuel_provider |

Curated rules:

- standardise timestamps to UTC plus local timezone attributes
- standardise vehicle identifiers
- map source event types to canonical event types
- retain source payload reference
- apply deduplication by event key and payload hash
- support late-arriving events
- support replay by event_date and feed_id
- avoid business metric calculations in this layer

---

## 7. IoT-Like Feed Types

## 7.1 Telematics Feed

Example event types:

- GPS location update
- odometer update
- engine hour update
- harsh braking
- speeding
- idle event
- trip start / trip end
- geofence entry / exit

Canonical event table:

```text
OPEN_CURATED_EVENTS.TELEMATICS_EVENT
```

Minimum fields:

```text
event_business_key
vehicle_id
provider_id
event_timestamp
event_date
latitude
longitude
speed
odometer_reading
engine_hours
event_type
payload_hash
source_payload_path
```

Feature outputs:

```text
FEATURES.FEATURE_VEHICLE_USAGE_DAILY
FEATURES.FEATURE_DRIVER_BEHAVIOUR_DAILY
FEATURES.FEATURE_VEHICLE_MAINTENANCE_RISK
```

Signal outputs:

```text
SIGNALS.SIGNAL_HIGH_UTILISATION
SIGNALS.SIGNAL_LOW_UTILISATION
SIGNALS.SIGNAL_MAINTENANCE_RISK
SIGNALS.SIGNAL_DRIVER_BEHAVIOUR_RISK
```

---

## 7.2 Vehicle Diagnostics Feed

Example event types:

- fault code detected
- battery warning
- engine warning
- tyre pressure warning
- service interval reached
- emissions diagnostic event

Canonical event table:

```text
OPEN_CURATED_EVENTS.VEHICLE_DIAGNOSTIC_EVENT
```

Feature outputs:

```text
FEATURES.FEATURE_VEHICLE_HEALTH_DAILY
FEATURES.FEATURE_FAULT_CODE_HISTORY
```

Signal outputs:

```text
SIGNALS.SIGNAL_CRITICAL_FAULT
SIGNALS.SIGNAL_RECURRING_FAULT
SIGNALS.SIGNAL_SERVICE_DUE
```

---

## 7.3 Driver App Feed

Example event types:

- app login
- inspection submitted
- issue reported
- trip confirmation
- document upload
- service request
- incident reported

Canonical event table:

```text
OPEN_CURATED_EVENTS.DRIVER_APP_EVENT
```

Feature outputs:

```text
FEATURES.FEATURE_DRIVER_APP_ENGAGEMENT
FEATURES.FEATURE_VEHICLE_APP_ACTIVITY_DAILY
```

Signal outputs:

```text
SIGNALS.SIGNAL_LOW_APP_ENGAGEMENT
SIGNALS.SIGNAL_REPORTED_VEHICLE_ISSUE
SIGNALS.SIGNAL_INCIDENT_REPORTED
```

Design note:

If no driver master exists, driver app signals must remain vehicle/client-linked rather than true person-level scoring.

---

## 7.4 EV Charging Feed

Example event types:

- charging session started
- charging session completed
- reimbursement claim submitted
- reimbursement approved
- high-cost charging session
- public charging event
- home charging event

Canonical event table:

```text
OPEN_CURATED_EVENTS.EV_CHARGING_EVENT
```

Feature outputs:

```text
FEATURES.FEATURE_EV_CHARGING_BEHAVIOUR
FEATURES.FEATURE_EV_COST_PER_KWH
```

Signal outputs:

```text
SIGNALS.SIGNAL_HIGH_COST_CHARGING
SIGNALS.SIGNAL_LOW_USAGE_HIGH_CHARGING
SIGNALS.SIGNAL_REIMBURSEMENT_EXCEPTION
```

---

## 7.5 Fuel Card Feed

Example event types:

- fuel transaction
- card assignment
- card status change
- high-value transaction
- declined transaction

Canonical event table:

```text
OPEN_CURATED_EVENTS.FUEL_CARD_EVENT
```

Feature outputs:

```text
FEATURES.FEATURE_FUEL_USAGE_DAILY
FEATURES.FEATURE_FUEL_COST_PER_KM
FEATURES.FEATURE_FUEL_CARD_BEHAVIOUR
```

Signal outputs:

```text
SIGNALS.SIGNAL_FUEL_ANOMALY
SIGNALS.SIGNAL_MULTIPLE_FILLS_SHORT_WINDOW
SIGNALS.SIGNAL_FUEL_WITHOUT_USAGE
```

---

## 7.6 CRM / Client Portal Feed

Example event types:

- client login
- service request
- invoice query
- complaint raised
- fleet report downloaded
- support case updated

Canonical event table:

```text
OPEN_CURATED_EVENTS.CLIENT_PORTAL_EVENT
```

Feature outputs:

```text
FEATURES.FEATURE_CLIENT_PORTAL_ENGAGEMENT
FEATURES.FEATURE_CLIENT_SERVICE_INTENSITY
```

Signal outputs:

```text
SIGNALS.SIGNAL_CLIENT_SERVICE_RISK
SIGNALS.SIGNAL_LOW_PORTAL_ENGAGEMENT
SIGNALS.SIGNAL_HIGH_SUPPORT_ACTIVITY
```

---

## 8. Feature Layer Design

Feature tables convert event history into reusable AI/ML-ready attributes.

Feature table naming:

```text
FEATURES.FEATURE_<SUBJECT>_<GRAIN>_<FREQUENCY>
```

Examples:

```text
FEATURES.FEATURE_VEHICLE_USAGE_DAILY
FEATURES.FEATURE_VEHICLE_HEALTH_DAILY
FEATURES.FEATURE_FUEL_COST_PER_KM_DAILY
FEATURES.FEATURE_EV_CHARGING_BEHAVIOUR_MONTHLY
FEATURES.FEATURE_SUPPLIER_PERFORMANCE_MONTHLY
FEATURES.FEATURE_CLIENT_FLEET_TCO_MONTHLY
```

Required feature metadata columns:

| Column | Purpose |
|---|---|
| `feature_set_id` | Feature set identifier |
| `feature_version` | Feature logic version |
| `feature_grain` | vehicle/day, client/month, supplier/month, etc. |
| `feature_window_start` | Start of feature calculation window |
| `feature_window_end` | End of feature calculation window |
| `source_event_count` | Number of events used |
| `dq_status` | Data quality status |
| `created_run_id` | Pipeline run identifier |
| `created_at` | Feature generation timestamp |

Feature principles:

- features must be reproducible
- feature logic must be versioned
- feature windows must be explicit
- feature grains must be declared
- features must link back to source event batches
- features should not contain uncontrolled PII

---

## 9. Signal Layer Design

Signals are governed, explainable indicators derived from features, rules, or model outputs.

Signal table naming:

```text
SIGNALS.SIGNAL_<BUSINESS_INDICATOR>
```

Examples:

```text
SIGNALS.SIGNAL_FUEL_ANOMALY
SIGNALS.SIGNAL_MAINTENANCE_RISK
SIGNALS.SIGNAL_HIGH_TCO
SIGNALS.SIGNAL_EV_CHARGING_EXCEPTION
SIGNALS.SIGNAL_SUPPLIER_PERFORMANCE_RISK
SIGNALS.SIGNAL_CLIENT_SERVICE_RISK
```

Required signal columns:

| Column | Purpose |
|---|---|
| `signal_id` | Unique signal identifier |
| `signal_type` | Type of signal |
| `signal_subject_type` | vehicle, client, supplier, contract, etc. |
| `signal_subject_id` | Business key or surrogate key |
| `signal_timestamp` | Time signal was generated |
| `signal_window_start` | Start of evaluation window |
| `signal_window_end` | End of evaluation window |
| `signal_score` | Numeric score where applicable |
| `signal_severity` | low, medium, high, critical |
| `signal_reason_code` | Explainable reason |
| `signal_version` | Rule/model version |
| `source_feature_set_id` | Source feature set |
| `source_event_count` | Number of supporting source events |
| `dq_status` | Data quality status |
| `ai_safe_flag` | Whether signal can be exposed to AI |
| `created_run_id` | Pipeline run identifier |
| `created_at` | Signal generation timestamp |

Signal principles:

- every signal must be explainable
- every signal must have a version
- every signal must have supporting evidence
- high-impact signals must not directly trigger automated decisions without review
- AI can explain signals but should not create unmanaged signal definitions

---

## 10. AI Consumption Layer

AI should consume:

```text
SEMANTIC certified views
GOLD business marts
FEATURES governed feature tables
SIGNALS governed signal tables
AI_KNOWLEDGE documentation
AUDIT evidence
```

AI should not directly consume:

```text
RAW_EVENTS
STAGED_EVENTS
uncertified event-store tables
unapproved experimental features
unapproved model outputs
```

AI consumption contract example:

```yaml
asset_name: SEMANTIC_VEHICLE_HEALTH
asset_type: semantic_view
grain: vehicle_id, event_date
approved_for_ai: true
allowed_use_cases:
  - fleet_operations_copilot
  - maintenance_summary_generation
  - executive_insight_generation
not_allowed_use_cases:
  - automated driver discipline
  - automated insurance decisioning
  - automated credit/pricing decision
freshness_sla: daily
sensitivity:
  - commercial_internal
  - vehicle_operational_data
owner: fleet_data_platform
evidence_required: true
```

---

## 11. Data Quality Requirements

| Check | Applies To | Action |
|---|---|---|
| Required event timestamp | all event feeds | reject record |
| Required event key | all event feeds | reject or generate deterministic key if allowed |
| Duplicate event key and payload | all event feeds | flag duplicate and exclude from curated output |
| Same event key with different payload | all event feeds | quarantine conflict |
| Invalid timestamp | all event feeds | reject record |
| Future timestamp beyond tolerance | all event feeds | quarantine |
| Late arrival beyond watermark | event feeds | retain and mark late |
| Vehicle ID missing | vehicle-linked feeds | reject or quarantine |
| Vehicle ID not found | curated/conformed join | quarantine or late-bind |
| Invalid coordinates | telematics | reject or null with warning depending on rule |
| Speed outside expected range | telematics | warning or reject depending on threshold |
| Negative cost | fuel, EV, maintenance | reject unless explicitly allowed |
| Invalid event type | all event feeds | quarantine |
| Schema drift | all feeds | quarantine unexpected fields unless additive drift is allowed |

DQ results must be written to:

```text
AUDIT.DQ_EVENT_RESULT
AUDIT.DQ_FEATURE_RESULT
AUDIT.DQ_SIGNAL_RESULT
```

---

## 12. Watermark and Late Arrival Handling

IoT-like feeds often arrive late or out of order.

Required watermark fields:

```text
event_timestamp
ingest_timestamp
processing_watermark
late_arrival_flag
late_arrival_reason
```

Recommended policy:

| Feed Type | Default Watermark |
|---|---|
| Telematics | event_date + 24 hours |
| Diagnostics | event_date + 48 hours |
| Driver app | event_date + 24 hours |
| EV charging | event_date + 72 hours |
| Fuel cards | transaction_date + 72 hours |
| CRM portal | event_date + 24 hours |

Late records should not be discarded by default. They should be:

```text
retained
flagged
reprocessed into affected partitions
audited
```

---

## 13. Replay and Reprocessing

Every Phase 3 pipeline must support replay by:

```text
feed_id
event_date
event_hour
ingest_run_id
batch_date
feature_version
signal_version
```

Replay rules:

- RAW is never overwritten.
- STAGED_EVENTS can be regenerated from RAW.
- OPEN_CURATED_EVENTS can be rebuilt by event_date partition.
- FEATURES can be rebuilt by feature window and feature_version.
- SIGNALS can be rebuilt by signal window and signal_version.
- Replayed outputs must write audit records.
- Replayed outputs must be idempotent.

---

## 14. Orchestration Pattern

Recommended execution sequence:

```text
1. Create pipeline run_id
2. Resolve active feed contracts
3. Ingest source payloads to RAW_EVENTS
4. Validate landing and write raw audit
5. Parse payloads to STAGED_EVENTS
6. Apply schema validation, dedupe, DQ, and watermark logic
7. Write rejects and quarantine records
8. Merge or append to OPEN_CURATED_EVENTS
9. Generate daily/hourly feature tables
10. Generate governed signal tables
11. Refresh Snowflake/Fabric semantic serving assets where applicable
12. Publish AI consumption metadata
13. Publish audit evidence pack
```

---

## 15. Metadata Contracts

Each feed must declare:

```yaml
feed_id: FEED_TELEMATICS_001
source_system_id: SRC_TELEMATICS_PROVIDER_001
feed_name: telematics_events
feed_type: iot_event
source_format: json
ingestion_mode: micro_batch
event_key_columns:
  - provider_event_id
event_timestamp_column: event_timestamp
watermark_policy: event_date_plus_24_hours
dedupe_policy: event_key_plus_payload_hash
schema_drift_policy: quarantine_unexpected_fields
target_raw_path: abfss://raw/.../feed=telematics_events/
target_staging_path: abfss://staging/.../feed=telematics_events/
target_curated_table: OPEN_CURATED_EVENTS.TELEMATICS_EVENT
ai_consumption_allowed: false
owner: fleet_data_platform
```

Feature contract example:

```yaml
feature_set_id: FEATURE_VEHICLE_USAGE_DAILY
feature_version: 1.0
grain: vehicle_id, event_date
source_tables:
  - OPEN_CURATED_EVENTS.TELEMATICS_EVENT
feature_window: daily
output_table: FEATURES.FEATURE_VEHICLE_USAGE_DAILY
approved_for_ai: true
owner: fleet_analytics
```

Signal contract example:

```yaml
signal_id: SIGNAL_MAINTENANCE_RISK
signal_version: 1.0
grain: vehicle_id, event_date
source_features:
  - FEATURES.FEATURE_VEHICLE_USAGE_DAILY
  - FEATURES.FEATURE_VEHICLE_HEALTH_DAILY
output_table: SIGNALS.SIGNAL_MAINTENANCE_RISK
approved_for_ai: true
requires_human_review: true
owner: fleet_operations
```

---

## 16. Security and Governance

IoT-like fleet feeds can contain sensitive operational information.

Sensitive categories may include:

- vehicle location
- driver behaviour
- incident reports
- app activity
- client service interactions
- fuel-card behaviour
- reimbursement behaviour
- commercially sensitive fleet cost data

Required controls:

| Control | Requirement |
|---|---|
| Classification | every feed, feature, and signal must have classification |
| Access control | raw and staged event data restricted to engineering roles |
| AI-safe flag | only approved semantic, feature, signal, and gold assets exposed to AI |
| Masking | sensitive attributes masked or excluded from AI views |
| Retention | event retention policy by feed type |
| Audit | all AI-facing asset access must be logged where possible |
| Purpose limitation | AI consumption contract must define allowed and disallowed use cases |

---

## 17. Acceptance Criteria

Phase 3 is complete when:

- IoT-like feed contracts are defined for telematics, diagnostics, driver app, EV charging, fuel-card, and CRM portal events.
- RAW_EVENTS paths preserve original payloads immutably.
- STAGED_EVENTS outputs are typed Parquet with required lineage columns.
- OPEN_CURATED_EVENTS tables are partitioned, replayable, and queryable.
- Watermark and late-arrival handling are implemented.
- Duplicate and conflict handling is implemented.
- Feature tables are generated for at least three priority use cases.
- Signal tables are generated for at least three priority use cases.
- Feature and signal registry metadata exists.
- AI consumption contracts exist for all AI-facing assets.
- Raw and staging data are not directly exposed to AI consumers.
- Audit evidence exists for event ingestion, feature generation, and signal generation.
- Reprocessing by event_date and feed_id is deterministic.
- Platform boundary between Data Lake, Snowflake/Fabric/Databricks, and AI consumption is documented.

---

## 18. Recommended Implementation Sequence

## Phase 3A — Lake Event Foundation

1. Define event feed metadata contracts.
2. Create RAW_EVENTS and STAGED_EVENTS path conventions.
3. Add event envelope columns.
4. Implement telematics and driver app feed prototypes.
5. Add DQ, dedupe, rejects, and audit.

## Phase 3B — Open Curated Event Store

1. Create OPEN_CURATED_EVENTS tables.
2. Add partitioning and replay logic.
3. Add late-arrival and watermark handling.
4. Validate event-store queries.
5. Expose selected event summaries to Snowflake or Fabric.

## Phase 3C — Feature Engineering

1. Build vehicle usage daily features.
2. Build EV charging behaviour features.
3. Build fuel anomaly features.
4. Build vehicle health features.
5. Register feature metadata and versions.

## Phase 3D — Signal Layer

1. Build maintenance risk signal.
2. Build fuel anomaly signal.
3. Build EV charging exception signal.
4. Build high-TCO signal.
5. Add signal evidence and reason codes.

## Phase 3E — AI Consumption

1. Create SEMANTIC AI-safe views.
2. Create AI consumption contracts.
3. Add retrieval-ready documentation.
4. Add audit evidence summaries.
5. Validate copilot access only to approved assets.

---

## 19. Summary

A concise explanation:

> Phase 3 changes the pipeline from a warehouse-first analytical pipeline into an AI-ready event lake architecture. For IoT-like fleet feeds, I would keep the lower layers open in ADLS using Parquet or Delta/Iceberg-compatible formats. Raw events are immutable, staged events are typed and validated, and open curated event stores are replayable. Feature and signal pipelines then turn event history into governed AI-ready inputs. Snowflake, Fabric, or another serving layer can expose conformed, gold, semantic, feature, and signal assets. The key is that AI should consume certified features, signals, metrics, and evidence — not uncontrolled raw event data.
