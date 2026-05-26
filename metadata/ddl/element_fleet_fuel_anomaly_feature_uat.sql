-- Element Fleet Services Fuel Anomaly Feature UAT.
-- Run after:
--   CALL FEATURES.BUILD_FEATURE_FUEL_ANOMALY_SCORE('2026-05-26');
--
-- Scope: FEATURES layer only.
-- Target: FEATURES.FEATURE_FUEL_ANOMALY_SCORE

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE FLEET_MVP_SIT_WH;
USE DATABASE FLEET_MVP_SIT;

CREATE SCHEMA IF NOT EXISTS AUDIT;

CREATE OR REPLACE TABLE AUDIT.FUEL_ANOMALY_FEATURE_UAT_RESULTS (
  TEST_ID VARCHAR,
  TEST_NAME VARCHAR,
  ACTUAL_VALUE NUMBER,
  EXPECTED_VALUE NUMBER,
  TEST_STATUS VARCHAR,
  TEST_NOTES VARCHAR,
  TESTED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- UAT001: Feature table row count must match the conformed fuel transaction population.
INSERT INTO AUDIT.FUEL_ANOMALY_FEATURE_UAT_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
SELECT
  'UAT001',
  'Feature row count matches fuel transactions',
  (SELECT COUNT(*) FROM FEATURES.FEATURE_FUEL_ANOMALY_SCORE),
  (SELECT COUNT(*) FROM CONFORMED.FACT_FUEL_TRANSACTION),
  IFF(
    (SELECT COUNT(*) FROM FEATURES.FEATURE_FUEL_ANOMALY_SCORE)
      = (SELECT COUNT(*) FROM CONFORMED.FACT_FUEL_TRANSACTION),
    'passed',
    'failed'
  ),
  'There should be one feature row per conformed fuel transaction.'
;

-- UAT002: Every fuel transaction id must be unique in the feature table.
INSERT INTO AUDIT.FUEL_ANOMALY_FEATURE_UAT_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
WITH duplicate_feature_keys AS (
  SELECT FUEL_TRANSACTION_ID
  FROM FEATURES.FEATURE_FUEL_ANOMALY_SCORE
  GROUP BY FUEL_TRANSACTION_ID
  HAVING COUNT(*) > 1
)
SELECT
  'UAT002',
  'Feature table has one row per transaction key',
  COUNT(*),
  0,
  IFF(COUNT(*) = 0, 'passed', 'failed'),
  'Duplicate feature rows would break transaction-level anomaly review.'
FROM duplicate_feature_keys;

-- UAT003: No conformed fuel transaction should be missing from the feature table.
INSERT INTO AUDIT.FUEL_ANOMALY_FEATURE_UAT_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
SELECT
  'UAT003',
  'No missing conformed fuel transactions',
  COUNT(*),
  0,
  IFF(COUNT(*) = 0, 'passed', 'failed'),
  'Every conformed fuel transaction should receive a feature score.'
FROM CONFORMED.FACT_FUEL_TRANSACTION TXN
LEFT JOIN FEATURES.FEATURE_FUEL_ANOMALY_SCORE FEA
  ON FEA.FUEL_TRANSACTION_ID = TXN.FUEL_TRANSACTION_ID
WHERE FEA.FUEL_TRANSACTION_ID IS NULL;

-- UAT004: Scores must be populated and bounded from 0 to 100.
INSERT INTO AUDIT.FUEL_ANOMALY_FEATURE_UAT_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
SELECT
  'UAT004',
  'Fuel anomaly score is populated and bounded',
  COUNT(*),
  0,
  IFF(COUNT(*) = 0, 'passed', 'failed'),
  'The rule-based MVP score must stay within the documented 0-100 range.'
FROM FEATURES.FEATURE_FUEL_ANOMALY_SCORE
WHERE FUEL_ANOMALY_SCORE IS NULL
   OR FUEL_ANOMALY_SCORE < 0
   OR FUEL_ANOMALY_SCORE > 100;

-- UAT005: Rows with positive score should expose at least one reason code.
INSERT INTO AUDIT.FUEL_ANOMALY_FEATURE_UAT_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
SELECT
  'UAT005',
  'Positive anomaly scores have reason codes',
  COUNT(*),
  0,
  IFF(COUNT(*) = 0, 'passed', 'failed'),
  'Explainability is required for flagged anomaly-review rows.'
FROM FEATURES.FEATURE_FUEL_ANOMALY_SCORE
WHERE FUEL_ANOMALY_SCORE > 0
  AND NULLIF(TRIM(ANOMALY_REASON_CODES), '') IS NULL;

-- UAT006: Zero-score rows should not carry reason codes.
INSERT INTO AUDIT.FUEL_ANOMALY_FEATURE_UAT_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
SELECT
  'UAT006',
  'Zero anomaly scores have no reason codes',
  COUNT(*),
  0,
  IFF(COUNT(*) = 0, 'passed', 'failed'),
  'Reason codes should only describe active anomaly signals.'
FROM FEATURES.FEATURE_FUEL_ANOMALY_SCORE
WHERE FUEL_ANOMALY_SCORE = 0
  AND NULLIF(TRIM(ANOMALY_REASON_CODES), '') IS NOT NULL;

-- UAT007: Score arithmetic should match the documented rules.
INSERT INTO AUDIT.FUEL_ANOMALY_FEATURE_UAT_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
SELECT
  'UAT007',
  'Score matches rule contribution arithmetic',
  COUNT(*),
  0,
  IFF(COUNT(*) = 0, 'passed', 'failed'),
  'Score should equal capped sum of high value, no usage, mismatch, and multiple-fill contributions.'
FROM FEATURES.FEATURE_FUEL_ANOMALY_SCORE
WHERE FUEL_ANOMALY_SCORE <> LEAST(
  100,
  IFF(HIGH_VALUE_TRANSACTION_FLAG, 30, 0)
    + IFF(NO_USAGE_MATCH_FLAG, 25, 0)
    + IFF(FUEL_CARD_VEHICLE_MISMATCH_FLAG, 30, 0)
    + IFF(MULTIPLE_FILL_FLAG, 15, 0)
);

-- UAT008: Surrogate keys should resolve when conformed dimensions contain matching current rows.
INSERT INTO AUDIT.FUEL_ANOMALY_FEATURE_UAT_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
SELECT
  'UAT008',
  'Resolved dimension keys are carried into features',
  COUNT(*),
  0,
  IFF(COUNT(*) = 0, 'passed', 'failed'),
  'When current conformed dimensions exist, feature rows should carry client_sk and vehicle_sk.'
FROM FEATURES.FEATURE_FUEL_ANOMALY_SCORE FEA
LEFT JOIN CONFORMED.DIM_CLIENT CLI
  ON CLI.CLIENT_ID = FEA.CLIENT_ID
 AND CLI.IS_CURRENT = TRUE
LEFT JOIN CONFORMED.DIM_VEHICLE VEH
  ON VEH.VEHICLE_ID = FEA.VEHICLE_ID
 AND VEH.IS_CURRENT = TRUE
WHERE (CLI.CLIENT_ID IS NOT NULL AND FEA.CLIENT_SK IS NULL)
   OR (VEH.VEHICLE_ID IS NOT NULL AND FEA.VEHICLE_SK IS NULL);

-- UAT009: Feature lineage columns must be populated.
INSERT INTO AUDIT.FUEL_ANOMALY_FEATURE_UAT_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
SELECT
  'UAT009',
  'Feature lineage is populated',
  COUNT(*),
  0,
  IFF(COUNT(*) = 0, 'passed', 'failed'),
  'Feature version, scored timestamp, batch date, and source hash support auditability.'
FROM FEATURES.FEATURE_FUEL_ANOMALY_SCORE
WHERE FEATURE_VERSION IS NULL
   OR SCORED_AT IS NULL
   OR BATCH_DATE IS NULL
   OR SOURCE_RECORD_HASH IS NULL;

-- UAT010: Batch date should match the requested feature build batch.
INSERT INTO AUDIT.FUEL_ANOMALY_FEATURE_UAT_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
SELECT
  'UAT010',
  'Batch date matches feature build date',
  COUNT(*),
  0,
  IFF(COUNT(*) = 0, 'passed', 'failed'),
  'The MVP feature run should be stamped with the requested batch date.'
FROM FEATURES.FEATURE_FUEL_ANOMALY_SCORE
WHERE BATCH_DATE <> '2026-05-26'::DATE;

-- UAT011: There should be at least one flagged row in the synthetic test population.
INSERT INTO AUDIT.FUEL_ANOMALY_FEATURE_UAT_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
SELECT
  'UAT011',
  'Synthetic test data produces anomaly candidates',
  COUNT(*),
  1,
  IFF(COUNT(*) >= 1, 'passed', 'failed'),
  'The UAT population should include at least one score above zero for review.'
FROM FEATURES.FEATURE_FUEL_ANOMALY_SCORE
WHERE FUEL_ANOMALY_SCORE > 0;

-- UAT012: Overall UAT status.
INSERT INTO AUDIT.FUEL_ANOMALY_FEATURE_UAT_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
SELECT
  'UAT012',
  'Fuel anomaly feature UAT failed-test count',
  COUNT_IF(TEST_STATUS = 'failed'),
  0,
  IFF(COUNT_IF(TEST_STATUS = 'failed') = 0, 'passed', 'failed'),
  'All prior fuel anomaly feature UAT checks should pass.'
FROM AUDIT.FUEL_ANOMALY_FEATURE_UAT_RESULTS
WHERE TEST_ID BETWEEN 'UAT001' AND 'UAT011';

SELECT
  TEST_ID,
  TEST_NAME,
  ACTUAL_VALUE,
  EXPECTED_VALUE,
  TEST_STATUS,
  TEST_NOTES,
  TESTED_AT
FROM AUDIT.FUEL_ANOMALY_FEATURE_UAT_RESULTS
ORDER BY TEST_ID;

-- Drill-through review sample for business testers.
SELECT
  FUEL_TRANSACTION_ID,
  FUEL_CARD_ID,
  VEHICLE_ID,
  CLIENT_ID,
  TRANSACTION_DATETIME,
  GROSS_AMOUNT,
  DISTANCE_KM,
  FUEL_COST_PER_KM,
  TRANSACTION_FREQUENCY_7D,
  FUEL_ANOMALY_SCORE,
  ANOMALY_REASON_CODES
FROM FEATURES.FEATURE_FUEL_ANOMALY_SCORE
WHERE FUEL_ANOMALY_SCORE > 0
ORDER BY FUEL_ANOMALY_SCORE DESC, GROSS_AMOUNT DESC
LIMIT 50;
