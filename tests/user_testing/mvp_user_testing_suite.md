# Fabric Foundry MVP User Testing Suite

## Purpose

Validate the MVP user journeys for Phase 0, Phase 1, Phase 1A, Phase 2, and partial Phase 4 using the synthetic `bb_datasets` project.

## Test Data Locations

| Phase | Location |
|---|---|
| Phase 0 | `/Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_0` |
| Phase 1 | `/Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_1` |
| Phase 1A | `/Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_1a` |
| Phase 2 | `/Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_2` |
| Phase 4 partial | `/Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_4_partial` |

## UT-001: Foundation Artefact Review

Preconditions:

- Repository is cloned locally.
- Phase 0 commit is present.

Steps:

1. Open `README.md`.
2. Review `docs/architecture.md`, `docs/metadata_model.md`, `docs/operating_model.md`, `docs/onboarding_new_dataset.md`, `docs/governance_design.md`, and `docs/release_process.md`.
3. Review `metadata/contracts/dataset_contract_template.yaml`.
4. Review `metadata/contracts/transformation_contract_template.yaml`.
5. Review `design/decisions/ADR-0001-framework-principles.md`.

Expected result:

- User can understand the framework architecture, operating model, metadata model, onboarding process, governance model, and release approach.
- Dataset and transformation contract templates are present and usable.

## UT-002: Metadata-Driven Ingestion Happy Path

Preconditions:

- `/Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_1/raw/population/population_by_age.tsv` exists.

Steps:

1. Run:

   ```bash
   uv run python fabric/notebooks/generic_ingestion_driver.py --dataset-id DS_REF_POPULATION_001 --dataset-root /Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_1 --audit-path /Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_1/audit/phase_1_ingestion_audit.jsonl
   ```

2. Open `/Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_1/landing/reference/population_by_age/population_by_age.tsv`.
3. Open `/Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_1/audit/phase_1_ingestion_audit.jsonl`.

Expected result:

- The landing file exists.
- Audit status is `SUCCESS`.
- Source and target record counts are both `12`.
- No dataset-specific copy logic is required in the driver.

## UT-003: Metadata-Driven Ingestion Missing Source

Preconditions:

- Use a temporary copy of Phase 1 metadata where the source path points to a missing file.

Steps:

1. Run the ingestion driver using the modified metadata file.
2. Open the audit output.

Expected result:

- Audit status is `FAILED`.
- Error message clearly identifies the missing source path.

## UT-004: Erwin Export Acquisition

Preconditions:

- `/Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_1a/erwin/exports/reference_data_model/v0_1` contains the four required Erwin CSV files.

Steps:

1. Run:

   ```bash
   uv run python fabric/notebooks/erwin_export_loader.py --export-path /Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_1a/erwin/exports/reference_data_model/v0_1 --output-path /Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_1a/erwin/staging/reference_data_model/v0_1
   ```

2. Open `erwin_ingestion_report.json`.
3. Open `erwin_staging.json`.

Expected result:

- Import status is `SUCCESS`.
- Object count is `1`.
- Column count is `2`.
- Mapping count is `3`.
- Full reconciliation is not performed in this phase.

## UT-005: Platform File Discovery

Preconditions:

- `/Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_1a/raw/population/population_by_age.tsv` exists.

Steps:

1. Run:

   ```bash
   uv run python fabric/notebooks/platform_metadata_discovery.py --dataset-root /Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_1a --dataset-id DS_REF_POPULATION_001 --path /raw/population/population_by_age.tsv --delimiter tab --output-path /Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_1a/discovery
   ```

2. Open `platform_discovery_report.json`.
3. Open `platform_discovery.json`.

Expected result:

- Discovery status is `SUCCESS`.
- File count is `1`.
- Column count is `2`.
- Schema inferred flag is `true`.

## UT-006: Population Transformation Happy Path

Preconditions:

- `/Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_2/raw/population/population_by_age.tsv` exists.
- `/Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_2/lookup/dim_country.csv` exists.

Steps:

1. Run:

   ```bash
   uv run python fabric/notebooks/generic_transform_driver.py --dataset-id DS_REF_POPULATION_001 --dataset-root /Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_2 --audit-path /Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_2/audit/phase_2_transform_audit.jsonl
   ```

2. Open `/Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_2/processed/population_by_age/population_by_age.csv`.
3. Open `/Users/emilygao/LocalDocuments/Projects/bb_datasets/phase_2/audit/phase_2_transform_audit.jsonl`.

Expected result:

- Output file exists.
- Audit status is `SUCCESS`.
- Output contains Australia and New Zealand rows.
- Age group columns are present.
- Invalid country code row is excluded.

## UT-007: Transformation Missing Lookup

Preconditions:

- Use a temporary Phase 2 dataset root with the raw file present and the lookup file missing.

Steps:

1. Run the generic transform driver against the temporary dataset root.
2. Open the transform audit output.

Expected result:

- Audit status is `FAILED`.
- Error message clearly identifies the missing lookup file or lookup input.

## UT-008: Generated Agent Artefact Review

Preconditions:

- Phase 4 partial commit is present.

Steps:

1. Review `agent/contracts/AGT_POP_001.yaml`.
2. Review prompt templates under `agent/prompts/`.
3. Review `metadata/seed/agent_task_metadata.json`.
4. Review `docs/mappings/population_by_age_mapping.md`.
5. Review `agent/generated_assets/AGT_POP_001/review_summary.md`.
6. Complete `agent/review_checklists/generated_transform_review.md`.

Expected result:

- Generated assets are registered with `active_flag: false`.
- Review status is `under_review`.
- Human approval is required before promotion.
- Runtime code contains no LLM calls.

## UT-009: Full Automated Regression

Preconditions:

- Local virtual environment has pytest available through `uv`.

Steps:

1. Run:

   ```bash
   uv run pytest
   ```

Expected result:

- All automated MVP tests pass.
