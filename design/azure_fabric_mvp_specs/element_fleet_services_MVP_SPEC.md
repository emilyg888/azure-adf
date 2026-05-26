# SPEC_MVP.md — Element Fleet Services MVP Data Pipeline

## 1. Delivery objective

Plug the synthetic Element Fleet Services Australia dataset package into the Fabric Foundry metadata-driven pipeline and deliver an MVP analytical foundation for fleet-management reporting.

The MVP proves that a multi-domain fleet source can be onboarded through metadata, landed immutably in ADLS RAW, parsed and quality checked in ADLS STAGING, and conformed into Snowflake dimensional and fact tables.

Dataset source package:

```text
/Users/emilygao/LocalDocuments/Projects/bb_datasets/element-fleet-services/
```

## 2. Layered architecture

```text
ADLS RAW
- CSV / JSON / original payload
- partition by source/date/hour
- immutable archive
        ↓
ADLS STAGING
- parsed
- schema checked
- exact duplicate detected
- mutable records versioned by source control timestamps
- load-audited
- exposed as Snowflake external staging tables where required
        ↓
Snowflake CONFORMED
- business keys
- client, vehicle, driver/app, supplier dimensions
- leasing, maintenance, fuel, claims, registration, billing, charging, remarketing facts
- event summaries for high-volume sources
        ↓
Snowflake GOLD, FEATURES, SEMANTIC, ML / AI consumption
- excluded from MVP scope; see `element_fleet_services_PHASE2_SPEC.md`
```

For higher-volume telemetry, CRM/client portal events, and driver app data, the MVP must not load every raw event directly into heavily modelled Snowflake tables unless a concrete consumption need is approved. The standard pattern is:

```text
Raw events in ADLS
        ↓
Partitioned Parquet event store, Iceberg-compatible when available
        ↓
Snowflake external or loaded staging
        ↓
Conformed event summaries and feature-ready aggregates
```

The aggregate feature layer itself is out of MVP scope; only the event-store and minimal conformed summaries are in scope. Phase two introduces Snowflake `GOLD`, `FEATURES`, and `SEMANTIC` only after clear consumption patterns are defined.

## 3. Source datasets

The current source contract is the schema in `metadata.json` and `data_dictionary.md`. Current CSV files at the package root include `effective_at` and `updated_at` on mutable tables. Any stale source file missing required source control columns must fail schema validation.

| Dataset | Rows | MVP source group | Primary key | Source timing / watermark | Source record pattern | Conformed treatment |
|---|---:|---|---|---|---|---|
| `clients.csv` | 18 | `fleet_master_data` | `client_id` | `updated_at`, `effective_at` | mutable entity version | `DIM_CLIENT` |
| `vehicles.csv` | 150 | `fleet_master_data` | `vehicle_id` | `updated_at`, `effective_at` | mutable entity version | `DIM_VEHICLE` |
| `leasing_contracts.csv` | 150 | `fleet_contracts` | `lease_id` | `updated_at`, `effective_at` | mutable contract version | `FACT_LEASE_CONTRACT` plus version history |
| `maintenance_vendors.csv` | 23 | `fleet_supplier_master` | `vendor_id` | `updated_at`, `effective_at` | mutable entity version | `DIM_SUPPLIER` |
| `maintenance_work_orders.csv` | 320 | `fleet_maintenance` | `work_order_id` | `updated_at`, `effective_at` | mutable workflow version | `FACT_MAINTENANCE_WORK_ORDER` plus version history |
| `fuel_cards.csv` | 105 | `fleet_fuel` | `fuel_card_id` | `updated_at`, `effective_at` | mutable entity version | `DIM_FUEL_CARD` |
| `fuel_card_transactions.csv` | 578 | `fleet_fuel` | `fuel_transaction_id` | `transaction_datetime` | immutable event | `FACT_FUEL_TRANSACTION` |
| `telematics_daily.csv` | 1190 | `fleet_telematics` | `telematics_event_id` | `event_date` | immutable daily observation | Parquet event store plus `FACT_TELEMATICS_DAILY_SUMMARY` |
| `insurance_claims.csv` | 85 | `fleet_claims` | `claim_id` | `updated_at`, `effective_at` | mutable workflow version | `FACT_INSURANCE_CLAIM` plus version history |
| `vehicle_registration_events.csv` | 150 | `fleet_registration` | `registration_event_id` | `updated_at`, `effective_at` | mutable workflow version | `FACT_REGISTRATION_EVENT` plus version history |
| `finance_billing_invoices.csv` | 240 | `fleet_finance` | `invoice_id` | `updated_at`, `effective_at` | mutable invoice version | `FACT_BILLING_INVOICE` plus version history |
| `crm_client_portal_events.csv` | 420 | `fleet_crm` | `portal_event_id` | `updated_at`, `effective_at` | mutable case/event version | Parquet event store plus `FACT_CLIENT_PORTAL_DAILY_SUMMARY` |
| `driver_app_events.csv` | 520 | `fleet_driver_app` | `driver_app_event_id` | `event_datetime` | immutable event | Parquet event store plus `FACT_DRIVER_APP_DAILY_SUMMARY` |
| `ev_charging_sessions.csv` | 360 | `fleet_ev` | `charging_session_id` | `updated_at`, `effective_at` | mutable reimbursement version | `FACT_EV_CHARGING_SESSION` plus version history |
| `remarketing_auction_results.csv` | 65 | `fleet_remarketing` | `remarketing_event_id` | `updated_at`, `effective_at` | mutable disposal outcome version | `FACT_REMARKETING_AUCTION_RESULT` plus version history |

## 4. MVP scope

### In scope

- Register the fleet source system and all 15 CSV datasets in metadata.
- Land all source files into immutable ADLS RAW paths.
- Stage all datasets as typed Parquet tables with exact duplicate detection and deterministic version handling.
- Capture schema checks, row counts, file checksums, exact duplicate counts, version conflict counts, and load audit details.
- Expose ADLS STAGING datasets as Snowflake staging inputs by external table or controlled load.
- Build Snowflake conformed dimensions and facts listed in section 7.
- Implement referential checks across `client_id`, `vehicle_id`, `vendor_id`, and `fuel_card_id`.
- Produce a runbook for onboarding, execution, validation, and rollback.

### Out of scope

- Snowflake `GOLD`, `FEATURES`, and `SEMANTIC` schemas.
- Semantic model, dashboard, and BI presentation layer.
- ML feature store, feature engineering, scoring outputs, and predictive models.
- Streaming ingestion.
- Full SCD Type 2 coverage beyond the selected mutable dimensions.
- Fine-grained PII masking beyond MVP classification and policy placeholders.
- Real production connectors for Element, Custom Fleet, telematics vendors, banks, insurers, or government registration systems.

## 5. ADLS RAW design

RAW preserves original payloads exactly as received. No parsing, type coercion, deduplication, or destructive overwrite is allowed.

Path convention:

```text
abfss://raw@<storage-account>.dfs.core.windows.net/
  source_system=element_fleet_services_synthetic/
  dataset=<dataset_name>/
  ingest_date=YYYY-MM-DD/
  ingest_hour=HH/
  run_id=<run_id>/
  <original_file_name>
```

RAW metadata requirements:

| Attribute | Requirement |
|---|---|
| Source format | CSV for current synthetic files; JSON and original payload supported by contract |
| Write mode | append-only |
| Partitioning | `source_system`, `dataset`, `ingest_date`, `ingest_hour`, `run_id` |
| Immutability | no update or delete in-place |
| Audit | file name, file size, checksum, row count where available, source modified timestamp, ingest timestamp |
| Recovery | reruns create a new `run_id`; failed run paths are retained |

## 6. ADLS STAGING design

STAGING converts RAW source files to governed, typed Parquet tables. This layer acts as the Snowflake staging boundary through external tables or controlled bulk loads. It remains source-shaped and does not replace a business-conformed Silver layer.

Path convention:

```text
abfss://staging@<storage-account>.dfs.core.windows.net/
  domain=fleet_management/
  dataset=<dataset_name>/
  batch_date=YYYY-MM-DD/
  part-*.parquet
```

Staging rules:

| Rule | Requirement |
|---|---|
| Parse | CSV headers must match the active dataset contract |
| Types | Dates, timestamps, numbers, booleans, and strings are cast from contract metadata |
| Schema check | fail on missing required columns; quarantine unexpected columns unless contract allows additive drift |
| Exact duplicate detection | identify duplicate payloads using declared primary key plus `_record_hash`; do not treat different same-key versions as duplicates |
| Mutable record versioning | retain one row per source record version using business key plus `effective_at`, `updated_at`, `_record_hash`, and file lineage |
| Latest resolution | derive `_is_latest_for_business_key` only when ordering by `updated_at`, `effective_at`, source file arrival metadata, and row lineage is deterministic |
| Load audit | record input rows, output rows, rejected rows, duplicate rows, checksum, run status |
| Rejected records | write to `staging_rejects/domain=fleet_management/dataset=<dataset_name>/run_id=<run_id>/` |
| Snowflake staging | external table or loaded table name `STG_FLEET.<dataset_name_upper>` |

### 6.1 Intra-day update handling

ADLS STAGING must handle multiple source files per day and multiple same-entity updates within the same day. It must not aggregate and must not collapse same-key records unless they are exact duplicate payloads.

Required staging lineage columns:

| Column | Purpose |
|---|---|
| `_source_system_id` | source system that produced the file |
| `_source_dataset_id` | dataset contract identifier |
| `_source_file_name` | original file name |
| `_source_file_path` | original RAW path |
| `_source_file_modified_at` | source file modified timestamp where available |
| `_source_row_number` | row position in the source file |
| `_ingest_run_id` | pipeline run that landed the row |
| `_ingest_timestamp` | pipeline receipt timestamp |
| `_batch_date` | logical batch date |
| `_record_hash` | hash of non-lineage source payload columns |
| `_is_exact_duplicate` | true when another row has the same business key, source timestamps, and record hash |
| `_is_latest_for_business_key` | true for the latest deterministically ordered source version |
| `_latest_resolution_status` | `resolved`, `ambiguous_same_timestamp`, or `not_applicable_event` |

Mutable source version identity:

```text
business_key + effective_at + updated_at + _record_hash + _source_file_name + _source_row_number
```

Latest-record ordering for mutable tables:

```text
updated_at desc,
effective_at desc,
_source_file_modified_at desc,
_ingest_timestamp desc,
_source_file_name desc,
_source_row_number desc
```

If two rows for the same business key have the same `updated_at`, same `effective_at`, and different `_record_hash`, staging must retain both rows and set `_latest_resolution_status = 'ambiguous_same_timestamp'` unless a source-specific sequence column is available. Snowflake CONFORMED loads must reject or quarantine ambiguous latest candidates rather than silently selecting one.

Immutable event datasets use their event timestamp and event id as identity. They may still receive multiple files per day, but latest-version logic is not applied.

STAGING latest flags are advisory inputs, not the final trust boundary. Snowflake CONFORMED must re-check eligibility before current-table merges.

## 7. Snowflake conformed model

Target database and schemas:

```text
FLEET_MVP.CONFORMED
FLEET_MVP.STG_FLEET
FLEET_MVP.AUDIT
```

### 7.1 Dimensions

| Table | Grain | Business key | Source |
|---|---|---|---|
| `DIM_CLIENT` | one row per client | `client_id` | `clients.csv` |
| `DIM_VEHICLE` | one row per vehicle | `vehicle_id` | `vehicles.csv` |
| `DIM_SUPPLIER` | one row per maintenance vendor | `vendor_id` | `maintenance_vendors.csv` |
| `DIM_FUEL_CARD` | one row per fuel card | `fuel_card_id` | `fuel_cards.csv` |
| `DIM_DATE` | one row per date | calendar date | generated |

Driver is not represented as a standalone source entity in the dataset. For MVP, driver app activity is modelled as vehicle/client-linked events, not as `DIM_DRIVER`. A `DIM_DRIVER` placeholder can be added later if a driver master source is introduced.

Dimension technical columns:

```text
<dimension>_sk
business_key
effective_from
effective_to
is_current
source_system_id
source_dataset_id
source_effective_at
source_updated_at
source_record_hash
created_run_id
updated_run_id
created_at
updated_at
```

MVP SCD handling:

- `DIM_CLIENT`, `DIM_VEHICLE`, `DIM_SUPPLIER`, and `DIM_FUEL_CARD` use SCD Type 2.
- Type 2 merge is driven by business key and `source_record_hash`.
- New business keys insert a new current dimension row.
- Changed business keys close the previous current row and insert a new current row.
- Full extracts are treated as authoritative snapshots for selected mutable dimensions.
- Missing records in a full extract use `soft_delete`: set `deleted_flag = true`, close `effective_to`, and set `is_current = false`.
- Delta extracts do not soft-delete missing records.
- Ambiguous latest records are quarantined and are not merged into current dimension rows.

### 7.2 Facts and version history

| Table | Grain | Primary event key | Required foreign keys |
|---|---|---|---|
| `FACT_LEASE_CONTRACT` | one row per lease | `lease_id` | `client_sk`, `vehicle_sk` |
| `FACT_MAINTENANCE_WORK_ORDER` | one row per work order | `work_order_id` | `client_sk`, `vehicle_sk`, `supplier_sk` |
| `FACT_FUEL_TRANSACTION` | one row per fuel transaction | `fuel_transaction_id` | `client_sk`, `vehicle_sk`, `fuel_card_sk` |
| `FACT_TELEMATICS_DAILY_SUMMARY` | one row per vehicle per event date/provider | `telematics_event_id` | `client_sk`, `vehicle_sk`, `date_sk` |
| `FACT_INSURANCE_CLAIM` | one row per claim | `claim_id` | `client_sk`, `vehicle_sk` |
| `FACT_REGISTRATION_EVENT` | one row per registration renewal event | `registration_event_id` | `client_sk`, `vehicle_sk` |
| `FACT_BILLING_INVOICE` | one row per invoice | `invoice_id` | `client_sk` |
| `FACT_CLIENT_PORTAL_DAILY_SUMMARY` | one row per client/date/channel/event type | derived summary key | `client_sk`, `date_sk` |
| `FACT_DRIVER_APP_DAILY_SUMMARY` | one row per client/vehicle/date/event type/platform | derived summary key | `client_sk`, `vehicle_sk`, `date_sk` |
| `FACT_EV_CHARGING_SESSION` | one row per charging session | `charging_session_id` | `client_sk`, `vehicle_sk` |
| `FACT_REMARKETING_AUCTION_RESULT` | one row per remarketing event | `remarketing_event_id` | `client_sk`, `vehicle_sk` |

Mutable facts maintain a current analytical fact plus a version history where the source record can change intra-day:

| Current table | Version history table |
|---|---|
| `FACT_LEASE_CONTRACT` | `HIST_LEASE_CONTRACT_VERSION` |
| `FACT_MAINTENANCE_WORK_ORDER` | `HIST_MAINTENANCE_WORK_ORDER_VERSION` |
| `FACT_INSURANCE_CLAIM` | `HIST_INSURANCE_CLAIM_VERSION` |
| `FACT_REGISTRATION_EVENT` | `HIST_REGISTRATION_EVENT_VERSION` |
| `FACT_BILLING_INVOICE` | `HIST_BILLING_INVOICE_VERSION` |
| `FACT_EV_CHARGING_SESSION` | `HIST_EV_CHARGING_SESSION_VERSION` |
| `FACT_REMARKETING_AUCTION_RESULT` | `HIST_REMARKETING_AUCTION_RESULT_VERSION` |

The current table loads only rows that Snowflake re-validates as eligible:

```sql
_is_latest_for_business_key = true
AND _latest_resolution_status = 'resolved'
AND _is_exact_duplicate = false
AND coalesce(_dq_status, 'passed') = 'passed'
AND required foreign keys resolve
```

The version history table loads every non-exact-duplicate source version that passes DQ. Ambiguous latest records are retained or quarantined for evidence, but are not merged into current conformed tables.

Append-only event tables such as telematics, driver app activity, and fuel-card transactions merge by event id. Missing event ids are never expired by full or delta loads.

Fact technical columns:

```text
event_business_key
source_system_id
source_dataset_id
batch_date
effective_at
source_updated_at
source_record_hash
created_run_id
created_at
```

## 8. Data quality requirements

| Check | Applies to | MVP behavior |
|---|---|---|
| Required key not null | all datasets | fail dataset load |
| Duplicate and version uniqueness | all datasets | exact duplicates are flagged; conflicting same-key mutable versions are retained or quarantined based on ordering status |
| Required source control timestamps | mutable datasets | fail staging load when `effective_at` or `updated_at` is missing |
| Same-key ambiguous latest record | mutable datasets | quarantine conflicting rows and prevent current CONFORMED merge |
| `client_id` exists | all client-linked tables | reject orphan records |
| `vehicle_id` exists | vehicle-linked tables | reject orphan records |
| `vendor_id` exists | maintenance work orders | reject orphan records |
| `fuel_card_id` exists | fuel transactions | reject orphan records |
| Date parse validity | all date/timestamp columns | reject invalid rows |
| Non-negative monetary values | financial, maintenance, fuel, EV, registration, remarketing | reject negative rows unless explicitly allowed |
| Percentage range | `gps_fix_rate_pct` | reject values outside 0 to 100 |
| Boolean parse validity | flags | reject invalid boolean tokens |

DQ results must be written to the existing audit framework and linked to `run_id`, `dataset_id`, `batch_date`, and source file checksum.

## 9. Metadata onboarding design

Add one source system:

```json
{
  "source_system_id": "SRC_ELEMENT_FLEET_SYNTH_001",
  "source_system_name": "Element Fleet Services Synthetic Dataset",
  "source_type": "file",
  "connection_name": "conn_local_or_adls_element_fleet_synthetic",
  "auth_method": "managed_identity",
  "owner": "fleet_data_platform",
  "active_flag": true
}
```

Dataset ID convention:

```text
DS_FLEET_<SUBJECT>_001
```

Examples:

| Dataset | Dataset ID | Load type | Frequency |
|---|---|---|---|
| `clients.csv` | `DS_FLEET_CLIENTS_001` | incremental | on demand |
| `vehicles.csv` | `DS_FLEET_VEHICLES_001` | incremental | on demand |
| `fuel_card_transactions.csv` | `DS_FLEET_FUEL_TXN_001` | incremental | daily |
| `telematics_daily.csv` | `DS_FLEET_TELEMATICS_DAILY_001` | incremental | daily |
| `crm_client_portal_events.csv` | `DS_FLEET_PORTAL_EVENTS_001` | incremental | daily |
| `driver_app_events.csv` | `DS_FLEET_DRIVER_APP_EVENTS_001` | incremental | daily |

Each source contract must declare:

- `source_path` under the dataset package or future ADLS landing location.
- `source_format: csv`.
- delimiter `,`.
- primary key columns.
- watermark column where available.
- source record pattern: `mutable_versioned` or `immutable_event`.
- mutable ordering columns: `updated_at`, `effective_at`, optional source sequence.
- expected columns and target data types.

Each target contract must declare both:

- RAW target path using the immutable partition convention.
- STAGING target path using the Parquet batch convention.

## 10. Pipeline orchestration

MVP pipeline parameters:

| Parameter | Purpose |
|---|---|
| `environment` | `dev`, `test`, or `prod` config selection |
| `dataset_group` | one of the fleet source groups from section 3 |
| `dataset_id` | optional single dataset override |
| `batch_date` | logical batch date |
| `load_type` | `full` or `delta` |
| `source_date` | source extract date when loading dated `full_sources` or `delta_sources` folders |
| `run_mode` | `manual`, `scheduled`, or `retry` |
| `full_refresh_flag` | force full reload for selected datasets |

Execution sequence:

```text
1. Create run_id
2. Resolve active fleet datasets from metadata
3. Copy original source files to ADLS RAW
4. Validate RAW landing and write audit
5. Parse RAW files into ADLS STAGING Parquet
6. Apply schema checks, type casts, exact duplicate detection, version ordering, and DQ rules
7. Register or refresh Snowflake staging external tables
8. Load or merge Snowflake CONFORMED dimensions
9. Load or merge Snowflake CONFORMED facts and summaries
10. Publish audit evidence pack
```

### 10.1 Full source processing

Full daily extract files are expected under:

```text
<source_root>/full_sources/YYYY-MM-DD/
```

The current synthetic source package uses dated folders:

```text
full_sources/2026-05-25/
full_sources/2026-05-26/
```

Each dated folder must include all 15 source tables plus `manifest.csv` with:

```text
source_date,table_name,row_count,extract_type,changed_from_previous_extract
```

Full-source handling:

| Rule | Requirement |
|---|---|
| Manifest validation | every in-scope source table must be present and row counts must match the manifest |
| Mutable sources | files are authoritative snapshots for the source date and may contain cumulative changes for that day |
| Immutable events | carried-forward event rows must merge by event id and must not create duplicate conformed facts |
| RAW archive | files land under RAW with `source_extract=<source_date>` |
| STAGING lineage | staged rows include `_load_type = full` and `_source_extract_date` |
| SCD Type 2 | Snowflake CONFORMED merges by business key and source record hash |
| Missing mutable records | for selected full-extract dimensions, missing keys trigger `soft_delete` in Snowflake CONFORMED |

Full-source mode is the preferred test path for validating SCD Type 2 behavior because it proves both changed-record versioning and missing-record soft-delete semantics from authoritative snapshots.

### 10.2 Delta source processing

Delta source files are expected under:

```text
<source_root>/delta_sources/YYYY-MM-DD/
```

The current synthetic source package uses dated folders:

```text
delta_sources/2026-05-25/
delta_sources/2026-05-26/
```

Each dated folder must include `manifest.csv` with:

```text
source_date,table_name,row_count,delta_type
```

Delta files include all source contract columns plus:

```text
delta_action
```

MVP delta handling:

| Rule | Requirement |
|---|---|
| Manifest validation | `source_date` and source row counts must match the manifest |
| Sparse extracts | only tables listed in the manifest are processed for that delta run |
| Schema validation | expected source columns plus `delta_action` are required |
| RAW archive | files land under RAW with `source_extract=<source_date>` |
| STAGING lineage | staged rows include `_load_type`, `_source_extract_date`, and `_delta_action` |
| Mutable updates | `UPDATE` rows are handled through the same `effective_at`, `updated_at`, `_record_hash`, and latest-resolution logic |
| Deletes | future `DELETE` rows should be retained in STAGING and applied in Snowflake CONFORMED merge logic; current synthetic delta files contain `UPDATE` actions only |

Delta mode is not a replacement for the initial full/root load. The expected sequence is:

```text
1. Run full load from root-level source files
2. Run delta loads by source_date in chronological order
3. Merge latest resolved mutable versions into Snowflake CONFORMED current tables
4. Merge all non-exact-duplicate mutable versions into history tables
```

Dependency order:

```text
clients
  ↓
vehicles ───────────────┐
maintenance_vendors     │
fuel_cards              │
  ↓                     ↓
all dependent facts and event summaries
```

## 11. Snowflake load strategy

| Layer | Strategy |
|---|---|
| `STG_FLEET` | external tables over ADLS STAGING Parquet or transient staging tables loaded from ADLS |
| Dimensions | deterministic merge on business key from latest resolved mutable versions |
| Transaction facts | deterministic merge on event business key or latest resolved mutable version, depending on source pattern |
| SCD Type 2 dimensions | merge by business key and source record hash; soft-delete missing rows only for authoritative full extracts |
| Append-only events | insert or merge by event id; never expire missing records |
| Version history | append or merge every non-exact-duplicate mutable source version by business key, source timestamps, delta action, and record hash |
| Event summaries | rebuild by `batch_date` partition for CRM, driver app, and telematics summary facts |
| Audit | append-only load audit records |

Snowflake CONFORMED must not blindly trust ADLS STAGING latest flags. Every current dimension or fact merge must re-check latest/resolved/non-duplicate status, DQ pass status, and required foreign-key resolution in SQL.

### 11.1 External table or controlled load

Use both patterns, depending on dataset type.

| Dataset type | Recommendation |
|---|---|
| Low/medium volume dimensions | Controlled load into transient `STG_FLEET` tables |
| Mutable workflow facts | Controlled load into transient `STG_FLEET` tables |
| High-volume telematics, portal, and app events | External table over partitioned ADLS STAGING Parquet first |
| Repeatedly queried event summaries | Materialise into Snowflake CONFORMED |
| Snowpark feature jobs | Excluded from MVP; phase two jobs should use conformed Snowflake tables, not raw external files |

Reasoning:

- Controlled loaded tables are easier for deterministic merges, DQ, joins, RI checks, and repeatable testing.
- External tables are useful for high-volume event stores where the platform should not always load every raw event into Snowflake.
- Daily summaries and feature tables should be materialised in Snowflake because they are consumed repeatedly.

The existing `framework/targets/snowflake_writer.py` is currently a placeholder. MVP implementation must either complete this writer or use Snowflake SQL orchestration from Fabric after ADLS STAGING outputs are created.

### 11.2 Snowflake SQL responsibilities

Use Snowflake SQL for deterministic warehouse modelling after ADLS STAGING is available.

| Function | MVP tool |
|---|---|
| External table creation over ADLS STAGING | Snowflake SQL |
| Transient staging table load | Snowflake SQL |
| Dimension SCD Type 2 merge | Snowflake SQL |
| Fact merge by event key | Snowflake SQL |
| Version history insert or merge | Snowflake SQL |
| Referential integrity checks | Snowflake SQL |
| Event summary rebuild by `batch_date` | Snowflake SQL first; Snowpark only if logic becomes complex |

Python/Fabric code should prepare RAW and STAGING data, validate source contracts, and publish lineage/audit metadata. It should not own deterministic warehouse merge semantics once data has reached Snowflake.

## 12. Security and governance

Sensitivity classification:

| Dataset | Classification | Notes |
|---|---|---|
| `clients.csv` | internal synthetic | client names are fabricated |
| `vehicles.csv` | internal synthetic | vehicle attributes only; no real VINs |
| `vehicle_registration_events.csv` | internal synthetic | plate numbers are synthetic but treated as sensitive-like |
| `crm_client_portal_events.csv` | internal synthetic | case activity may become sensitive in real source |
| `driver_app_events.csv` | internal synthetic | no driver identity in MVP source |
| all remaining datasets | internal synthetic | no real personal, customer, or supplier data |

Production adaptation must revisit PII, PCI, telemetry location sensitivity, driver privacy, retention rules, and access controls before connecting to real systems.

## 13. MVP acceptance criteria

- All 15 datasets are registered in metadata with source, RAW target, STAGING target, primary key, and expected schema.
- A single parameterised run can ingest all fleet datasets from the source package.
- RAW output preserves the original files under immutable run partitions.
- STAGING output is Parquet, typed, exact-duplicate checked, version-aware, and audited.
- Multiple intra-day files and same-entity source updates are retained in STAGING with deterministic current-record flags or explicit ambiguity flags.
- Full source folders are processed by manifest, with all 15 source tables present and `_source_extract_date` carried into STAGING.
- Delta source folders are processed by manifest, with `_delta_action` and `_source_extract_date` carried into STAGING.
- Snowflake staging can read all ADLS STAGING datasets.
- Snowflake conformed dimensions and facts are built with surrogate keys and referential checks.
- Snowflake CONFORMED current tables load only latest resolved mutable versions; ambiguous same-key latest records are quarantined.
- High-volume sources are available in event-store form, with only daily summary facts modelled in Snowflake CONFORMED.
- Audit logs show row counts, rejected counts, duplicate counts, status, and error details per dataset.
- Re-running the same batch is deterministic and does not corrupt prior RAW archives.

## 14. Implementation backlog

1. Create fleet dataset contracts from `metadata.json` and `data_dictionary.md`.
2. Add fleet metadata seed file for source systems, datasets, source contracts, and target contracts.
3. Extend ingestion driver to support RAW and STAGING outputs in one run, or add a staging driver after RAW landing.
4. Add schema and DQ rules for the fleet datasets.
5. Add mutable-version staging logic for `effective_at`, `updated_at`, `_record_hash`, source file lineage, and latest resolution flags.
6. Add dated full-source mode for `full_sources/<source_date>/`, manifest validation, and SCD Type 2 test coverage.
7. Add delta-source mode for `delta_sources/<source_date>/`, manifest validation, and `delta_action` lineage.
8. Implement Snowflake staging DDL generation for ADLS STAGING Parquet.
9. Implement conformed DDL and merge SQL for dimensions.
10. Implement conformed DDL and merge SQL for facts, version history, deletes, and event summaries.
11. Add local tests using the source package row counts, join-key constraints, intra-day same-key updates, ambiguous latest scenarios, full-source SCD behavior, and delta manifests.
12. Add an operator runbook and validation checklist.
