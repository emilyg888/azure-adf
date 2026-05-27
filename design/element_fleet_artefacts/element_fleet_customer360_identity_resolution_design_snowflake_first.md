# Use Case — Identity Resolution for Customer 360

## 1. Executive Narrative

Identity resolution is a foundational Customer 360 capability for a fleet-management business.

Element Fleet / Custom Fleet data is likely spread across leasing, billing, vehicle master, fuel cards, maintenance, claims, telematics, EV charging, CRM, and client portal systems. The same customer or vehicle can appear under different identifiers, names, contracts, devices, cards, and operational relationships.

The purpose of this use case is to create a governed identity foundation:

```text
fragmented source records
  ↓
standardised entities
  ↓
deterministic + fuzzy matching
  ↓
golden customer / vehicle / account records
  ↓
crosswalks and relationship tables
  ↓
Customer 360 semantic view
```

The important design decision is that this does **not automatically require Databricks**.

Recommended delivery narrative:

> Start Snowflake-first. Use Snowflake SQL and Snowpark Python to deliver deterministic matching, fuzzy candidate generation, survivorship, crosswalks, golden entities, review queues, and Customer 360 semantic views. Introduce Databricks only when the workload becomes graph-heavy, ML-heavy, lakehouse-native, or requires high-volume IoT identity stitching across large event stores.

This is a pragmatic architecture position that keeps the first production version governed and Snowflake-first while still recognising lakehouse trade-offs.

---

## 2. Business Problem

Fleet-management data is naturally fragmented.

A client may appear as:

```text
ABC Logistics Pty Ltd
ABC Logistics
A.B.C. Logistics Australia
ABC Logistics - NSW Branch
```

The same vehicle may be referenced by:

```text
vehicle_id
VIN
registration plate
lease_id
fuel_card_id
telematics_device_id
driver_app_vehicle_id
```

The same customer relationship may span:

```text
leasing
billing
maintenance
claims
fuel cards
EV charging
driver app
client portal
CRM
telematics
```

Without identity resolution, analytics becomes unreliable:

- duplicate clients
- fragmented vehicle history
- incorrect total cost of ownership
- missing maintenance-risk patterns
- incomplete client profitability view
- unreliable AI/copilot answers
- poor cross-sell and service insight
- inaccurate operational reporting

---

## 3. Target Business Outcome

Create a governed Customer 360 foundation that answers:

- Who is the client?
- Which vehicles belong to the client?
- Which contracts, invoices, fuel cards, claims, service events, charging sessions, and portal interactions relate to that client?
- What is the total cost and utilisation profile of the fleet?
- Which customers have rising service risk, high support activity, or expansion opportunity?
- Which entities are confidently matched, and which require human review?

---

## 4. Recommended Delivery Position

## 4.1 Snowflake-First

The first version should be delivered inside Snowflake unless there is a clear reason not to.

```text
ADLS RAW / STAGING
        ↓
Snowflake STG_FLEET
        ↓
Snowflake IDENTITY
        ↓
Snowflake GOLDEN
        ↓
Snowflake SEMANTIC.CUSTOMER_360
```

Why Snowflake-first makes sense:

| Reason                              | Explanation                                                                                      |
| ----------------------------------- | ------------------------------------------------------------------------------------------------ |
| Keeps operating model simpler       | Avoids adding Databricks unless scale or ML complexity justifies it                              |
| Good fit for SQL-first matching     | Deterministic matching, blocking, scoring, survivorship, and crosswalks can be done in Snowflake |
| Strong governed serving layer       | Customer 360 can be exposed through secure semantic views                                        |
| Snowpark fills Python gaps          | More complex standardisation and scoring can run inside Snowflake                                |
| Better for first production version | Easier to govern, test, deploy, and operationalise                                               |

---

## 4.2 When Databricks Is Justified

Databricks becomes justified when the workload has one or more of these characteristics:

| Trigger                               | Why Databricks May Be Better                                       |
| ------------------------------------- | ------------------------------------------------------------------ |
| Very large match graph                | Connected-component clustering and graph resolution at large scale |
| High-volume IoT identity stitching    | Device → vehicle → driver/app → client over billions of events     |
| Heavy ML entity resolution            | Embeddings, advanced similarity models, model training             |
| Data gravity is in the lakehouse      | Curated source data and event history already live in Delta/ADLS   |
| Data science team owns matching logic | Notebook-driven experimentation and ML lifecycle                   |
| Near-real-time identity updates       | Streaming identity updates from telematics/device feeds            |

Example Databricks-friendly identity chain:

```text
telematics_device_id
  ↓
vehicle_id
  ↓
lease_id
  ↓
customer_id
  ↓
golden_customer_id
```

If this chain must be resolved over billions of raw telemetry and device events, Databricks becomes a more natural engineering environment.

---

## 5. Snowflake Delivery Architecture

Recommended Snowflake schemas:

```text
FLEET_MVP.STG_FLEET
FLEET_MVP.IDENTITY
FLEET_MVP.GOLDEN
FLEET_MVP.CONFORMED
FLEET_MVP.GOLD
FLEET_MVP.SEMANTIC
FLEET_MVP.AUDIT
```

High-level flow:

```text
ADLS RAW
  ↓
ADLS STAGING Parquet
  ↓
Snowflake STG_FLEET
  ↓
IDENTITY.STD_* tables
  ↓
IDENTITY.MATCH_CANDIDATE_* tables
  ↓
GOLDEN.GOLDEN_* tables
  ↓
GOLDEN.XREF_* and REL_* tables
  ↓
GOLD.CUSTOMER_360_MART
  ↓
SEMANTIC.CUSTOMER_360
```

---

## 6. Source Inputs

Typical input datasets:

| Source Domain  | Example Input                                     |
| -------------- | ------------------------------------------------- |
| Client master  | `clients.csv`, CRM account records                |
| Leasing        | leasing contracts, lease account IDs              |
| Vehicle master | vehicle records, VIN, registration, vehicle class |
| Fuel card      | fuel card assignments, fuel transactions          |
| Telematics     | telematics device ID, GPS/device feed, odometer   |
| Driver app     | app vehicle ID, app user/device activity          |
| Maintenance    | work orders, vendor records, vehicle references   |
| Claims         | insurance claims, incident records                |
| Billing        | invoices, billing accounts                        |
| EV charging    | charging sessions, reimbursement records          |
| Portal / CRM   | client portal activity, service cases             |

---

## 7. Target Outputs

## 7.1 Standardised Entity Tables

```text
IDENTITY.STD_CUSTOMER
IDENTITY.STD_VEHICLE
IDENTITY.STD_ACCOUNT
IDENTITY.STD_FUEL_CARD
IDENTITY.STD_DEVICE
IDENTITY.STD_SUPPLIER
```

Purpose:

- clean and standardise source identifiers
- normalise names, addresses, domains, phone numbers, registration plates, VINs, device IDs
- retain source lineage
- create match-ready attributes

---

## 7.2 Match Candidate Tables

```text
IDENTITY.CUSTOMER_MATCH_CANDIDATE
IDENTITY.VEHICLE_MATCH_CANDIDATE
IDENTITY.DEVICE_VEHICLE_MATCH_CANDIDATE
IDENTITY.ACCOUNT_CUSTOMER_MATCH_CANDIDATE
```

Example columns:

```text
candidate_id
entity_type
source_record_a
source_record_b
match_score
match_method
match_reason_code
auto_match_flag
review_required_flag
created_run_id
created_at
```

---

## 7.3 Golden Entity Tables

```text
GOLDEN.GOLDEN_CUSTOMER
GOLDEN.GOLDEN_VEHICLE
GOLDEN.GOLDEN_ACCOUNT
GOLDEN.GOLDEN_SUPPLIER
GOLDEN.GOLDEN_FUEL_CARD
GOLDEN.GOLDEN_DRIVER_PLACEHOLDER
```

Design note:

If no trusted driver master exists, driver-related data should remain vehicle/client-linked rather than person-level scoring.

---

## 7.4 Crosswalk Tables

Crosswalk tables preserve traceability from source records to golden entities.

```text
GOLDEN.XREF_CUSTOMER_SOURCE
GOLDEN.XREF_VEHICLE_SOURCE
GOLDEN.XREF_ACCOUNT_SOURCE
GOLDEN.XREF_FUEL_CARD_SOURCE
GOLDEN.XREF_DEVICE_SOURCE
GOLDEN.XREF_SUPPLIER_SOURCE
```

Example:

| golden_customer_id | source_system | source_customer_id | match_confidence | match_method     |
| ------------------ | ------------- | ------------------ | ---------------: | ---------------- |
| GCUST_000123       | CRM           | CUST-9182          |             0.98 | deterministic    |
| GCUST_000123       | Billing       | BILL-7710          |             0.91 | fuzzy_name_abn   |
| GCUST_000123       | Leasing       | LSE-4490           |             0.96 | contract_account |

---

## 7.5 Relationship Tables

```text
GOLDEN.REL_CUSTOMER_VEHICLE
GOLDEN.REL_CUSTOMER_CONTRACT
GOLDEN.REL_VEHICLE_FUEL_CARD
GOLDEN.REL_VEHICLE_TELEMATICS_DEVICE
GOLDEN.REL_CUSTOMER_PORTAL_ACCOUNT
GOLDEN.REL_VEHICLE_DRIVER_APP_PROFILE
```

---

## 7.6 Customer 360 View

```text
SEMANTIC.CUSTOMER_360
```

Example fields:

```text
golden_customer_id
customer_name
customer_segment
active_vehicle_count
active_contract_count
monthly_tco
maintenance_cost_90d
fuel_cost_90d
ev_charging_cost_90d
open_claim_count
portal_activity_score
service_risk_score
fleet_growth_opportunity_score
data_quality_status
identity_resolution_confidence
```

---

## 8. Matching Method

## 8.1 Step 1 — Standardise Source Fields

Standardisation reduces false non-matches.

Examples:

| Field                | Standardisation                                           |
| -------------------- | --------------------------------------------------------- |
| customer name        | uppercase, remove punctuation, legal suffix normalisation |
| ABN / tax ID         | strip spaces, validate format                             |
| address              | standardise street type, postcode, suburb                 |
| phone                | country code normalisation                                |
| email/domain         | lowercase, extract business domain                        |
| vehicle registration | uppercase, remove separators                              |
| VIN                  | uppercase, validate length/pattern                        |
| fuel card number     | hash/mask sensitive value                                 |
| device ID            | trim, uppercase, provider namespace                       |

Snowflake SQL example:

```sql
CREATE OR REPLACE TABLE IDENTITY.STD_CUSTOMER AS
SELECT
    source_system_id,
    source_customer_id,
    customer_name,
    UPPER(REGEXP_REPLACE(customer_name, '[^A-Z0-9 ]', '')) AS std_customer_name_raw,
    TRIM(REGEXP_REPLACE(
        REGEXP_REPLACE(UPPER(customer_name), '\\bPTY LTD\\b|\\bLIMITED\\b|\\bLTD\\b', ''),
        '\\s+',
        ' '
    )) AS std_customer_name,
    REGEXP_REPLACE(abn, '[^0-9]', '') AS std_abn,
    LOWER(email_domain) AS std_email_domain,
    postcode AS std_postcode,
    created_run_id
FROM STG_FLEET.CLIENTS;
```

---

## 8.2 Step 2 — Deterministic Matching

Use exact or high-confidence identifiers first.

Examples:

| Entity            | Deterministic Match                    |
| ----------------- | -------------------------------------- |
| Customer          | ABN / legal entity ID / CRM account ID |
| Vehicle           | VIN / internal vehicle ID              |
| Contract          | lease ID                               |
| Fuel card         | fuel card ID                           |
| Telematics device | provider device ID                     |
| Supplier          | vendor ID / ABN                        |

Example:

```text
If ABN matches → same golden customer
If VIN matches → same golden vehicle
If fuel_card_id matches → same golden fuel card
```

Snowflake SQL pattern:

```sql
CREATE OR REPLACE TABLE IDENTITY.CUSTOMER_MATCH_DETERMINISTIC AS
SELECT
    c1.source_customer_id AS source_record_a,
    c2.source_customer_id AS source_record_b,
    'customer' AS entity_type,
    1.0 AS match_score,
    'deterministic_abn' AS match_method,
    'same_abn' AS match_reason_code
FROM IDENTITY.STD_CUSTOMER c1
JOIN IDENTITY.STD_CUSTOMER c2
  ON c1.std_abn = c2.std_abn
 AND c1.source_customer_id < c2.source_customer_id
WHERE c1.std_abn IS NOT NULL
  AND LENGTH(c1.std_abn) > 0;
```

---

## 8.3 Step 3 — Candidate Pair Generation

Do not fuzzy-match every record against every other record.

Use blocking keys to reduce comparison volume.

Example blocking keys:

```text
customer_name_prefix + postcode
business_domain + postcode
abn_prefix
vehicle_registration + state
vin_prefix
client_id + vehicle_id
```

Snowflake SQL example:

```sql
CREATE OR REPLACE TABLE IDENTITY.STD_CUSTOMER_BLOCKED AS
SELECT
    *,
    CONCAT(SUBSTR(std_customer_name, 1, 5), '_', std_postcode) AS blocking_key
FROM IDENTITY.STD_CUSTOMER;
```

---

## 8.4 Step 4 — Fuzzy Matching

Use fuzzy matching where deterministic keys are missing or inconsistent.

Snowflake can support moderate fuzzy matching using SQL string functions and Snowpark Python.

Possible match features:

| Feature               | Description                     |
| --------------------- | ------------------------------- |
| name similarity       | customer name similarity        |
| address similarity    | address or postcode match       |
| email domain match    | business domain similarity      |
| phone match           | normalised phone number         |
| ABN partial match     | partial tax identifier          |
| contract relationship | same lease/billing relationship |
| vehicle relationship  | overlapping vehicle assignments |

Example scoring logic:

```text
match_score =
  0.40 * name_similarity
+ 0.20 * address_similarity
+ 0.15 * email_domain_match
+ 0.15 * phone_match
+ 0.10 * relationship_overlap
```

Thresholds:

|     Score | Action               |
| --------: | -------------------- |
|   >= 0.95 | auto-match           |
| 0.85–0.95 | match with warning   |
| 0.70–0.85 | send to review queue |
|    < 0.70 | no match             |

Snowflake SQL-style example:

```sql
CREATE OR REPLACE TABLE IDENTITY.CUSTOMER_MATCH_CANDIDATE AS
SELECT
    a.source_customer_id AS source_record_a,
    b.source_customer_id AS source_record_b,
    'customer' AS entity_type,
    1 - (
        EDITDISTANCE(a.std_customer_name, b.std_customer_name)
        / NULLIF(GREATEST(LENGTH(a.std_customer_name), LENGTH(b.std_customer_name)), 0)
    ) AS name_similarity,
    IFF(a.std_postcode = b.std_postcode, 1.0, 0.0) AS postcode_match,
    (
        0.80 * name_similarity
      + 0.20 * postcode_match
    ) AS match_score,
    CASE
        WHEN match_score >= 0.95 THEN 'auto_match'
        WHEN match_score >= 0.75 THEN 'review'
        ELSE 'no_match'
    END AS match_action
FROM IDENTITY.STD_CUSTOMER_BLOCKED a
JOIN IDENTITY.STD_CUSTOMER_BLOCKED b
  ON a.blocking_key = b.blocking_key
 AND a.source_customer_id < b.source_customer_id;
```

---

## 8.5 Step 5 — Graph / Cluster Resolution

Identity matching often creates transitive relationships.

Example:

```text
A matches B
B matches C
Therefore A, B, C belong to the same entity cluster
```

In Snowflake, a first version can avoid complex graph processing by:

- assigning golden IDs from deterministic keys
- processing auto-match candidate pairs iteratively
- storing cluster membership in crosswalk tables
- pushing uncertain cases to review

If clustering becomes large, deeply connected, or iterative, this is where Databricks may become more appropriate.

---

## 8.6 Step 6 — Survivorship Rules

Survivorship determines the best value for the golden record.

Example rules:

| Attribute              | Preferred Source         |
| ---------------------- | ------------------------ |
| legal customer name    | CRM or master data       |
| billing name           | billing system           |
| active contract status | leasing system           |
| current fleet size     | vehicle assignment table |
| contact details        | CRM                      |
| cost metrics           | billing / finance        |
| service interactions   | portal / CRM             |
| vehicle status         | vehicle master / leasing |

Example:

```text
Golden customer name = CRM legal name if present
Else billing legal name
Else most recent source name
```

Survivorship rule output should include:

```text
survivorship_rule_version
attribute_source_system
attribute_source_record_id
attribute_last_updated_at
```

---

## 8.7 Step 7 — Human Review Queue

Not all matches should be automated.

Create review output:

```text
GOVERNANCE.IDENTITY_REVIEW_QUEUE
```

Fields:

```text
review_case_id
entity_type
candidate_record_a
candidate_record_b
match_score
match_reason
conflicting_attributes
recommended_action
review_status
reviewed_by
reviewed_at
```

This avoids silently merging uncertain records.

---

## 9. Customer 360 Construction

After golden IDs and crosswalks are created, Customer 360 can be assembled.

```text
GOLDEN_CUSTOMER
  ↓
REL_CUSTOMER_VEHICLE
  ↓
contracts + fuel + maintenance + claims + billing + charging + portal + telematics
  ↓
CUSTOMER_360
```

Example Customer 360 domains:

| Domain             | Example Metrics                                                |
| ------------------ | -------------------------------------------------------------- |
| Fleet profile      | active vehicles, vehicle class mix, EV ratio                   |
| Contract profile   | active leases, expiry dates, contract value                    |
| Cost profile       | TCO, maintenance cost, fuel cost, EV cost                      |
| Risk profile       | open claims, anomaly signals, maintenance risk                 |
| Engagement profile | portal activity, service cases, app adoption                   |
| Growth profile     | service penetration, underused products, expansion opportunity |

---

## 10. AI Consumption Pattern

Customer 360 should be exposed to AI through governed semantic views, not raw identity-resolution tables.

Recommended AI-facing assets:

```text
SEMANTIC.CUSTOMER_360
SEMANTIC.CUSTOMER_FLEET_COST_SUMMARY
SEMANTIC.CUSTOMER_SERVICE_RISK_SUMMARY
SEMANTIC.CUSTOMER_GROWTH_OPPORTUNITY
SIGNALS.SIGNAL_CUSTOMER_SERVICE_RISK
SIGNALS.SIGNAL_HIGH_TCO_CUSTOMER
```

AI-safe answer pattern:

```text
User asks:
"Why is this client’s fleet cost increasing?"

AI retrieves:
- certified TCO metric
- maintenance cost trend
- fuel/EV cost trend
- vehicle utilisation trend
- open claims
- supplier performance signals
- identity resolution confidence

AI answers:
"Fleet cost increased mainly because maintenance cost rose 18% over the last quarter across 12 high-utilisation vehicles. The result is based on certified Customer 360 data with identity resolution confidence of 0.96."
```

---

## 11. Governance Requirements

| Governance Area           | Requirement                                                          |
| ------------------------- | -------------------------------------------------------------------- |
| Match confidence          | every matched entity must carry a confidence score                   |
| Match method              | deterministic, fuzzy, graph, manual                                  |
| Golden ID lineage         | every golden entity links back to source records                     |
| Survivorship rule version | golden attributes must record rule version                           |
| Human review              | medium-confidence matches require review                             |
| Auditability              | every run writes match counts, merge counts, review counts           |
| Explainability            | match reason codes must be stored                                    |
| Privacy                   | sensitive identifiers must be masked or hashed                       |
| AI safety                 | AI should see certified Customer 360 views, not raw match candidates |

---

## 12. Data Quality Checks

| Check                                             | Action                              |
| ------------------------------------------------- | ----------------------------------- |
| Missing customer name and no stable identifier    | quarantine                          |
| Duplicate source customer ID                      | reject or quarantine                |
| Invalid ABN / tax ID format                       | warning or reject depending on rule |
| Same VIN assigned to multiple active customers    | review queue                        |
| Same fuel card linked to multiple active vehicles | review queue                        |
| Same vehicle active under multiple leases         | review queue                        |
| Conflicting legal names with same ABN             | review queue                        |
| Low confidence fuzzy match                        | review queue                        |
| Golden entity with no source lineage              | fail pipeline                       |

---

## 13. Snowflake vs Databricks Decision Matrix

| Requirement                           | Snowflake-First                                                  | Databricks Candidate                     |
| ------------------------------------- | ---------------------------------------------------------------- | ---------------------------------------- |
| Deterministic matching                | Strong fit                                                       | Also possible                            |
| Moderate fuzzy matching               | Strong fit with SQL/Snowpark                                     | Also possible                            |
| Customer 360 semantic views           | Strong fit                                                       | Needs serving layer                      |
| Governance, masking, RBAC             | Strong fit                                                       | Strong if lakehouse governance is mature |
| Review queue tables                   | Strong fit                                                       | Also possible                            |
| Golden entity and crosswalk tables    | Strong fit                                                       | Also possible                            |
| Large graph clustering                | Possible but less natural                                        | Stronger fit                             |
| ML-based entity resolution            | Possible with Snowpark ML, but limited for heavy experimentation | Stronger fit                             |
| High-volume IoT identity stitching    | Possible after summarisation                                     | Stronger fit over event lake             |
| Notebook-based data science workflows | Less natural                                                     | Stronger fit                             |

Recommended decision:

```text
For MVP / first production version:
Snowflake-first

For large-scale IoT / ML / graph-heavy expansion:
Consider Databricks or lakehouse extension
```

---

## 14. Implementation Roadmap

## Phase 1 — Snowflake Deterministic Resolution

- Standardise client, vehicle, contract, billing, and fuel-card identifiers.
- Match on ABN, VIN, lease ID, vehicle ID, fuel card ID.
- Create crosswalk tables.
- Create first Customer 360 semantic view.

## Phase 2 — Snowflake Fuzzy Matching

- Add name/address/domain matching.
- Add blocking strategy.
- Add match confidence score.
- Add review queue.
- Add survivorship rules.
- Use Snowpark Python where SQL becomes awkward.

## Phase 3 — Governed Customer 360

- Add golden customer and golden vehicle IDs.
- Add customer-vehicle-contract-fuel-card-device relationship tables.
- Add TCO, service risk, and fleet profile metrics.
- Add AI-safe semantic views.

## Phase 4 — Lakehouse / Databricks Extension If Needed

- Add graph-style identity clustering.
- Add high-volume telematics identity stitching.
- Add ML-based matching features.
- Add large-scale event-driven identity updates.
- Publish outputs back to Snowflake semantic serving layer where required.

---

## 15. Success Metrics

| Metric                       | Target                                                    |
| ---------------------------- | --------------------------------------------------------- |
| deterministic match rate     | high for records with stable identifiers                  |
| duplicate customer reduction | measurable reduction in duplicate client records          |
| review queue rate            | manageable volume for data stewards                       |
| false merge rate             | near zero for auto-matched records                        |
| Customer 360 completeness    | increasing coverage across domains                        |
| AI-safe coverage             | certified semantic views available for priority use cases |
| lineage completeness         | every golden entity links to source records               |
| confidence coverage          | every match has method and score                          |

---

## 16. Final concise explanation:

Roadmap: deliver the first version of Customer 360 identity resolution inside Snowflake. The solution needs standardisation, deterministic matching, fuzzy candidate generation, survivorship rules, golden customer and vehicle records, source crosswalks, review queues, and semantic Customer 360 views. Snowflake SQL is a good fit for the deterministic and governed parts, while Snowpark Python can handle more complex scoring and standardisation logic. Introduce Databricks only if we move into large-scale graph matching, ML-heavy identity resolution, or high-volume IoT identity stitching over lakehouse event stores.
