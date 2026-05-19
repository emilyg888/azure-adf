# Onboarding New Dataset

1. Assign a dataset id using `DS_<DOMAIN>_<SUBJECT>_<SEQUENCE>`.
2. Create or update the dataset contract from `metadata/contracts/dataset_contract_template.yaml`.
3. Register source system, dataset, source contract, and target contract metadata.
4. Add schema mapping and transformation rule metadata if transformation is required.
5. Add governance rules for DQ, PII, lineage, and certification requirements.
6. Add synthetic sample data under the test dataset project.
7. Run metadata validation, ingestion SIT, transformation unit tests, and user testing scenarios.
8. Attach test evidence to the pull request.
9. Obtain required human approvals before production use.
