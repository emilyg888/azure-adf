# Release Process

## MVP Flow

1. Implement changes on a feature branch or controlled local branch.
2. Run unit tests for changed framework modules.
3. Run SIT tests using synthetic datasets from `bb_datasets`.
4. Capture run evidence in audit output.
5. Commit phase changes separately.
6. Push to the repository.
7. Review generated or material transformation changes before runtime use.

## Pull Request Evidence

- Summary of change
- Impacted dataset
- Impacted source and target
- Mapping changes
- Test command and result
- Generated code summary, if applicable
- Review checklist and approval decision
