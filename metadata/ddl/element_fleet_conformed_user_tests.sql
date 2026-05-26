-- Element Fleet Services CONFORMED layer user tests.
-- Run after `element_fleet_snowflake_sit_setup.sql` or the equivalent MVP load.
--
-- Current SIT coverage: CONFORMED.DIM_CLIENT SCD Type 2 from the two full extracts.
-- Expected source dates:
--   2026-05-25: initial full snapshot
--   2026-05-26: second full snapshot with 8 changed client records

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE FLEET_MVP_SIT_WH;
USE DATABASE FLEET_MVP_SIT;

CREATE SCHEMA IF NOT EXISTS AUDIT;

CREATE OR REPLACE TABLE AUDIT.CONFORMED_USER_TEST_RESULTS (
  TEST_ID VARCHAR,
  TEST_NAME VARCHAR,
  ACTUAL_VALUE NUMBER,
  EXPECTED_VALUE NUMBER,
  TEST_STATUS VARCHAR,
  TEST_NOTES VARCHAR,
  TESTED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- UT001: The conformed dimension has exactly one current row per source client.
INSERT INTO AUDIT.CONFORMED_USER_TEST_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
SELECT
  'UT001',
  'DIM_CLIENT current row count',
  COUNT(*),
  18,
  IFF(COUNT(*) = 18, 'passed', 'failed'),
  'Current client dimension rows should match the latest full extract business-key count.'
FROM CONFORMED.DIM_CLIENT
WHERE IS_CURRENT = TRUE;

-- UT002: SCD2 closed rows exist for the 8 client records changed between the two full extracts.
INSERT INTO AUDIT.CONFORMED_USER_TEST_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
SELECT
  'UT002',
  'DIM_CLIENT closed changed row count',
  COUNT(*),
  8,
  IFF(COUNT(*) = 8, 'passed', 'failed'),
  'Changed client hashes should close old current rows and insert new current rows.'
FROM CONFORMED.DIM_CLIENT
WHERE IS_CURRENT = FALSE
  AND DELETED_FLAG = FALSE;

-- UT003: No clients were missing from the second full extract, so no soft deletes should exist.
INSERT INTO AUDIT.CONFORMED_USER_TEST_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
SELECT
  'UT003',
  'DIM_CLIENT soft deleted row count',
  COUNT(*),
  0,
  IFF(COUNT(*) = 0, 'passed', 'failed'),
  'Soft deletes only occur when an authoritative full extract omits a previously current business key.'
FROM CONFORMED.DIM_CLIENT
WHERE DELETED_FLAG = TRUE;

-- UT004: No business key should have more than one current row.
INSERT INTO AUDIT.CONFORMED_USER_TEST_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
WITH duplicate_current AS (
  SELECT CLIENT_ID
  FROM CONFORMED.DIM_CLIENT
  WHERE IS_CURRENT = TRUE
  GROUP BY CLIENT_ID
  HAVING COUNT(*) > 1
)
SELECT
  'UT004',
  'DIM_CLIENT one current row per business key',
  COUNT(*),
  0,
  IFF(COUNT(*) = 0, 'passed', 'failed'),
  'SCD Type 2 dimensions must have at most one current row per business key.'
FROM duplicate_current;

-- UT005: No SCD2 date ranges should be invalid.
INSERT INTO AUDIT.CONFORMED_USER_TEST_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
SELECT
  'UT005',
  'DIM_CLIENT valid effective date ranges',
  COUNT(*),
  0,
  IFF(COUNT(*) = 0, 'passed', 'failed'),
  'Every SCD2 row should have EFFECTIVE_FROM before EFFECTIVE_TO.'
FROM CONFORMED.DIM_CLIENT
WHERE EFFECTIVE_FROM IS NULL
   OR EFFECTIVE_TO IS NULL
   OR EFFECTIVE_FROM >= EFFECTIVE_TO;

-- UT006: Current conformed client hashes should match the latest eligible 2026-05-26 source rows.
INSERT INTO AUDIT.CONFORMED_USER_TEST_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
WITH latest_source AS (
  SELECT CLIENT_ID, _RECORD_HASH
  FROM STG_FLEET.CLIENTS_EXT
  WHERE _BATCH_DATE = '2026-05-26'
    AND _IS_LATEST_FOR_BUSINESS_KEY = TRUE
    AND _LATEST_RESOLUTION_STATUS = 'resolved'
    AND _IS_EXACT_DUPLICATE = FALSE
    AND COALESCE(_DQ_STATUS, 'passed') = 'passed'
),
mismatched_current AS (
  SELECT TGT.CLIENT_ID
  FROM CONFORMED.DIM_CLIENT TGT
  JOIN latest_source SRC
    ON SRC.CLIENT_ID = TGT.CLIENT_ID
  WHERE TGT.IS_CURRENT = TRUE
    AND TGT.SOURCE_RECORD_HASH <> SRC._RECORD_HASH
)
SELECT
  'UT006',
  'DIM_CLIENT current rows match latest source hash',
  COUNT(*),
  0,
  IFF(COUNT(*) = 0, 'passed', 'failed'),
  'Snowflake CONFORMED must not retain stale current hashes after the second full extract.'
FROM mismatched_current;

-- UT007: The source itself shows 8 changed client hashes across the two full extracts.
INSERT INTO AUDIT.CONFORMED_USER_TEST_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
WITH day1 AS (
  SELECT CLIENT_ID, _RECORD_HASH
  FROM STG_FLEET.CLIENTS_EXT
  WHERE _BATCH_DATE = '2026-05-25'
    AND _IS_LATEST_FOR_BUSINESS_KEY = TRUE
    AND _LATEST_RESOLUTION_STATUS = 'resolved'
),
day2 AS (
  SELECT CLIENT_ID, _RECORD_HASH
  FROM STG_FLEET.CLIENTS_EXT
  WHERE _BATCH_DATE = '2026-05-26'
    AND _IS_LATEST_FOR_BUSINESS_KEY = TRUE
    AND _LATEST_RESOLUTION_STATUS = 'resolved'
),
changed_source_keys AS (
  SELECT D1.CLIENT_ID
  FROM day1 D1
  JOIN day2 D2
    ON D2.CLIENT_ID = D1.CLIENT_ID
  WHERE D1._RECORD_HASH <> D2._RECORD_HASH
)
SELECT
  'UT007',
  'Source changed client hash count',
  COUNT(*),
  8,
  IFF(COUNT(*) = 8, 'passed', 'failed'),
  'This proves the expected SCD2 change population exists in the full extracts.'
FROM changed_source_keys;

-- UT008: Every changed source key should have exactly one closed historical row in CONFORMED.
INSERT INTO AUDIT.CONFORMED_USER_TEST_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
WITH day1 AS (
  SELECT CLIENT_ID, _RECORD_HASH
  FROM STG_FLEET.CLIENTS_EXT
  WHERE _BATCH_DATE = '2026-05-25'
    AND _IS_LATEST_FOR_BUSINESS_KEY = TRUE
    AND _LATEST_RESOLUTION_STATUS = 'resolved'
),
day2 AS (
  SELECT CLIENT_ID, _RECORD_HASH
  FROM STG_FLEET.CLIENTS_EXT
  WHERE _BATCH_DATE = '2026-05-26'
    AND _IS_LATEST_FOR_BUSINESS_KEY = TRUE
    AND _LATEST_RESOLUTION_STATUS = 'resolved'
),
changed_source_keys AS (
  SELECT D1.CLIENT_ID
  FROM day1 D1
  JOIN day2 D2
    ON D2.CLIENT_ID = D1.CLIENT_ID
  WHERE D1._RECORD_HASH <> D2._RECORD_HASH
),
bad_history AS (
  SELECT C.CLIENT_ID
  FROM changed_source_keys C
  LEFT JOIN CONFORMED.DIM_CLIENT TGT
    ON TGT.CLIENT_ID = C.CLIENT_ID
   AND TGT.IS_CURRENT = FALSE
   AND TGT.DELETED_FLAG = FALSE
  GROUP BY C.CLIENT_ID
  HAVING COUNT(TGT.CLIENT_ID) <> 1
)
SELECT
  'UT008',
  'Changed source keys have one closed historical row',
  COUNT(*),
  0,
  IFF(COUNT(*) = 0, 'passed', 'failed'),
  'Each changed client should have exactly one expired historical version after two full extracts.'
FROM bad_history;

-- UT009: No ambiguous latest records should have been merged into CONFORMED current rows.
INSERT INTO AUDIT.CONFORMED_USER_TEST_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
WITH ambiguous_source AS (
  SELECT DISTINCT CLIENT_ID
  FROM STG_FLEET.CLIENTS_EXT
  WHERE _LATEST_RESOLUTION_STATUS <> 'resolved'
)
SELECT
  'UT009',
  'Ambiguous latest source rows excluded from current dimension',
  COUNT(*),
  0,
  IFF(COUNT(*) = 0, 'passed', 'failed'),
  'Ambiguous latest records must be quarantined and must not become current CONFORMED rows.'
FROM CONFORMED.DIM_CLIENT TGT
JOIN ambiguous_source SRC
  ON SRC.CLIENT_ID = TGT.CLIENT_ID
WHERE TGT.IS_CURRENT = TRUE;

-- UT010: The conformed test audit itself should contain only passed checks.
INSERT INTO AUDIT.CONFORMED_USER_TEST_RESULTS
  (TEST_ID, TEST_NAME, ACTUAL_VALUE, EXPECTED_VALUE, TEST_STATUS, TEST_NOTES)
SELECT
  'UT010',
  'CONFORMED user test pass count',
  COUNT_IF(TEST_STATUS = 'failed'),
  0,
  IFF(COUNT_IF(TEST_STATUS = 'failed') = 0, 'passed', 'failed'),
  'All prior user tests in this run should pass.'
FROM AUDIT.CONFORMED_USER_TEST_RESULTS
WHERE TEST_ID BETWEEN 'UT001' AND 'UT009';

SELECT
  TEST_ID,
  TEST_NAME,
  ACTUAL_VALUE,
  EXPECTED_VALUE,
  TEST_STATUS,
  TEST_NOTES,
  TESTED_AT
FROM AUDIT.CONFORMED_USER_TEST_RESULTS
ORDER BY TEST_ID;

-- Drill-through evidence for testers: changed clients and their current/history rows.
WITH day1 AS (
  SELECT CLIENT_ID, CLIENT_NAME, CLIENT_STATUS, UPDATED_AT, EFFECTIVE_AT, _RECORD_HASH
  FROM STG_FLEET.CLIENTS_EXT
  WHERE _BATCH_DATE = '2026-05-25'
),
day2 AS (
  SELECT CLIENT_ID, CLIENT_NAME, CLIENT_STATUS, UPDATED_AT, EFFECTIVE_AT, _RECORD_HASH
  FROM STG_FLEET.CLIENTS_EXT
  WHERE _BATCH_DATE = '2026-05-26'
),
changed_source_keys AS (
  SELECT D1.CLIENT_ID
  FROM day1 D1
  JOIN day2 D2
    ON D2.CLIENT_ID = D1.CLIENT_ID
  WHERE D1._RECORD_HASH <> D2._RECORD_HASH
)
SELECT
  TGT.CLIENT_ID,
  TGT.CLIENT_NAME,
  TGT.CLIENT_STATUS,
  TGT.EFFECTIVE_FROM,
  TGT.EFFECTIVE_TO,
  TGT.IS_CURRENT,
  TGT.DELETED_FLAG,
  TGT.SOURCE_UPDATED_AT,
  TGT.SOURCE_RECORD_HASH
FROM CONFORMED.DIM_CLIENT TGT
JOIN changed_source_keys C
  ON C.CLIENT_ID = TGT.CLIENT_ID
ORDER BY TGT.CLIENT_ID, TGT.EFFECTIVE_FROM;
